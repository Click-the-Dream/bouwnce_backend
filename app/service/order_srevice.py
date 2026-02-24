from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import status
from fastapi.requests import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import genrate_verification_code
from app.models.cart import Cart
from app.models.order import Order, ProductMetadata
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.products import product_domain
from app.models.store import Store
from app.models.suborder import SubOrder
from app.models.user import User
from app.schemas.order import CheckoutInputSchema
from app.service.payment.paystack import paystack_service
from app.utils.exception import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    GoneException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.helper import generate_order_track_id, generate_suborder_track_id
from app.utils.responses import response_builder
from app.worker.tasks.email import send_email_using_worker


class OrderService:
    def __init__(self):
        self._max_tries = 5

    async def verify_payment(
        self, current_user: User, referenceToken: str, redis: Redis, db: AsyncSession
    ):
        # Verirfy payment using reference token
        is_success, response = paystack_service.callback(referenceToken)
        if is_success:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Payment  successful",
                data=response,
            )

        # Check if order is present, then update the order and payment as failed
        order = await Order.get_by_reference(referenceToken, db)
        if not order:
            raise ConflictException(message="order attached to reference not found")

        # Verify order is for user
        if str(current_user.id) != str(order.user_id):
            raise ForbiddenException(message="Order not yours")

        await order.update(db, {"status": "failed"})
        await Payment.update_by_id(str(order.payment_id), {"status": "failed"}, db)

        # Release reserved products
        products = [ProductMetadata(**product) for product in order.products]
        await Order.release_reserved_products(products, str(order.user_id), redis)

        raise BadRequestException(message="Payment failed of incomplete")

    async def get_cart_shipping_info(
        self, user: User, db: AsyncSession
    ) -> dict[str, Any]:

        # extract unique store ids from carts

        product_ids = [cart.product_id for cart in user.carts]
        if not product_ids:
            raise BadRequestException(message="User has no product in cart")

        products = await product_domain.get_products_by_ids(product_ids)

        store_ids = {product.store_id for product in products}
        stores: list[Store] = await Store.get_store_by_ids(list(store_ids), db)

        store_shipping_info = [
            {
                "store_id": str(store.id),
                "store_name": store.name,
                "shipment_info": store.shipment_info,
            }
            for store in stores
        ]

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully fetched cart shipping info",
            data=store_shipping_info,
        )

    async def checkout(
        self,
        user: User,
        shipment_infos: list[CheckoutInputSchema],
        redis: Redis,
        request: Request,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Create a checkout for user and return payment url

        steps:
            1. check for avaialabilty
            2. reserve product
            3. compute total price
            3. create payent intent
            4. create payment with status initiated
            5. create order with status initiated
            6. return the payment athorization url and list of unavailable products
        """

        try:
            idempotent_key = request.headers.get("Idempotent-key")
            if not idempotent_key:
                raise BadRequestException("Missing idempotent key")

            # Check if the order has been created before using the idempotent key
            # Return the response if order already exist to avoid duplicate processing
            order = await Order.get_by_idempotent_key(idempotent_key, db)
            if order is not None:
                reserved_products = order.products
                payment = await Payment.get_by_id(order.payment_id, db)
                authorization_url = payment.payment_url

                # Will include unavailable field to the response field when needed
                return response_builder(
                    status_code=status.HTTP_200_OK,
                    status="success",
                    message="Successfully checkout user",
                    data={
                        "payment_url": authorization_url,
                        "available_products": reserved_products,
                    },
                )

            # Get all the carts of a user

            carts_data = await Cart.get_by_user_id(
                user_id=str(user.id), db=db, all=True
            )
            carts = carts_data["data"]

            if not carts:
                raise BadRequestException(message="User has no product in cart")

            # Check the  availability of the products in the carts
            avaialble_products, unavailable_products = (
                await Order.check_cart_availability(carts, redis)
            )

            try:
                # Reserve those available products
                reserved_product, cannot_reserve_products = (
                    await Order.reserve_products(
                        avaialble_products, str(user.id), redis
                    )
                )

                # Add all the products that cannot be reserved to unvailable products
                unavailable_products.extend(cannot_reserve_products)

                if not reserved_product:
                    raise GoneException(
                        message="No product in user cart is available anymore",
                        data={
                            "available_products": [],
                            "unavailable_products": unavailable_products,
                        },
                    )

                # Group reserved product by store
                grouped_products = Order.group_products_by_store(reserved_product)

                # Fetch all stores for the products

                store_ids = [key for key in grouped_products]
                stores = await Store.get_by_ids(store_ids, db)
                if len(stores) != len(store_ids):
                    raise BadRequestException("One or more stores are not found")

                store_dict = {str(store.id): store for store in stores}

                # Total shipping fee
                total_shipping_fee = 0

                # Flatten Shipment info
                shipment_info_dict = {
                    shipment.store_id: shipment.shipment_id
                    for shipment in shipment_infos
                }

                for store_id, store in store_dict.items():
                    if store_id not in shipment_info_dict:
                        raise BadRequestException(
                            "User has Product from store but has not selected shipping option for store"
                        )

                    shipment_id = shipment_info_dict[store_id]
                    matched_shipment = next(
                        (s for s in store.shipment_info if str(s.id) == shipment_id),
                        None,
                    )
                    if not matched_shipment:
                        raise BadRequestException(
                            f"Shipment: {shipment_id} doesn't belong to store: {store_id}"
                        )

                    grouped_products[store_id]["shipping_info"] = {
                        "fee": matched_shipment.delivery_fee,
                        "shipping_id": matched_shipment.id,
                    }

                    total_shipping_fee += int(matched_shipment.delivery_fee)

                # Compute the total ammount
                total_price = (
                    Order.compute_total_amount(reserved_product) + total_shipping_fee
                )

                payment_data = {
                    "email": user.email,
                    "amount": total_price * 100,  # convert to kobo
                }
            except BadRequestException:
                raise
            except GoneException:
                raise
            except Exception as e:
                print("Error occured while checking user cart out: ", str(e))

                # Release all the reserved products
                try:
                    await Order.release_reserved_products(
                        reserved_product, str(user.id), redis
                    )
                except Exception as e:
                    print("Error occured while releasing reserved products: ", str(e))

                raise InternalServerErrorException(
                    message="Error occured while checking out user cart"
                ) from None

            try:
                authorization_url, referenceToken = (
                    paystack_service.create_payment_intent(payment_data)
                )
            except Exception as e:
                print("Error occured while creating payment intent: ", str(e))

                # Release all the reserved products
                try:
                    await Order.release_reserved_products(
                        reserved_product, str(user.id), redis
                    )
                except Exception as e:
                    print("Error occured while releasing reserved products: ", str(e))

                raise InternalServerErrorException(
                    message="Error occured while creating payment intent"
                ) from None

            # Create payment and order
            payment_data = {
                "user_id": user.id,
                "amount": total_price,
                "provider": "paystack",
                "provider_payment_id": referenceToken,
                "payment_url": authorization_url,
            }
            payment = await Payment.create(payment_data, db)

            order_data = {
                "user_id": user.id,
                "payment_id": payment.id,
                "total_amount": total_price,
                "username": user.username,
                "products": grouped_products,
                "idempotent_key": idempotent_key,
                "reference_token": referenceToken,
                "track_id": generate_order_track_id(),
            }

            await Order.create(order_data, db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully checkout user",
                data={
                    "payment_url": authorization_url,
                    "available_products": reserved_product,
                    "unavailable_products": unavailable_products,
                },
            )

        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def handle_successful_payment(
        self, request: Request, db: AsyncSession, redis: Redis
    ) -> dict[str, Any]:

        # Verify paystack webhook signature
        await paystack_service.verify_webhook_signature(request)

        body = await request.json()

        # Only handle charge.success event
        event = body.get("event")
        if event and event != "charge.success":
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="ignore event",
            )

        data = body["data"]
        reference = data["reference"]
        order = await Order.get_by_reference(reference, db)

        if not order:
            raise BadRequestException(message="Invalid reference Token")

        # If the order status is not initiated or abandoned (for late payment), then the order has been processed in one away or the other
        if order.status not in ["initiated", "abandoned"]:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Order has been processed",
            )

        # Confirm the amount paid is eqal to order amount
        if (order.total_amount * 100) != data["amount"]:  # Convert to naira from kobo
            raise ConflictException(message="amount mismatch")

        # The username of the user is needed for the suborder
        user = await Order.fetch_owner_of_order(str(order.user_id), db)
        if not user:
            raise ConflictException(message="no user for order found")

        grouped_products_by_store = order.products

        now = datetime.now(UTC)
        year = now.year

        # Create Suborders and order items
        for store_product in grouped_products_by_store:
            store_id, products_data = next(iter(store_product.items()))
            # Generate Otp
            store = await Store.get_by_id(store_id, db)
            otp = genrate_verification_code()

            suborder_data = {
                "store_id": store_id,
                "order_id": order.id,
                "total_amount": products_data["total_amount"],
                "otp": otp,
                "username": user.username,
                "status": "paid",
                "track_id": generate_suborder_track_id(),
            }
            suborder = await SubOrder.create(suborder_data, db)

            for product in products_data["products"]:
                order_item_data = {
                    "product_id": product["id"],
                    "suborder_id": suborder.id,
                    "quantity": product["quantity"],
                    "product_snapshot": {
                        "name": product["name"],
                        "store_id": product["store_id"],
                        "category": product["category"],
                        "images": product["images"],
                    },
                    "unit_price": product["amount"],
                    "line_price": Decimal(product["amount"]) * product["quantity"],
                }
                await OrderItem.create(order_item_data, db)

                # Decrease the stock and increase total sales of product (can be pushed to worker)
                await product_domain.decrease_product_stock_and_increase_total_sales(
                    product["id"], product["quantity"]
                )

            # Release all the reserved products (can be pushed to worker)
            await Order.release_reserved_products(
                products_data["products"], str(user.id), redis
            )

            # update store's wallet (can be pushed to worker)
            await store.update_store_wallet(amount=products_data["total_amount"], db=db)

            # Send email to vendor for order
            context = {
                "vendor_name": store.name,
                "username": user.username,
                "track_id": str(suborder.track_id),
                "order_link": "#",
                "year": year,
            }
            template = "vendor_alert_order.html"
            email_to = store.email
            subject = "New Order"

            send_email_using_worker.delay(
                email_to=email_to,
                subject=subject,
                context=context,
                template_name=template,
            )

        # Mark Both order and payment paid and successful respectively
        await order.update(db, {"status": "paid"})
        await Payment.update_by_id(str(order.payment_id), {"status": "successful"}, db)

        # Clear User cart
        await Cart.delete_by_user_id(str(user.id), db)

        # Send an email to buyer that order has been received
        context = {
            "customer_name": user.username,
            "year": year,
            "track_id": str(order.track_id),
            "order_date": now.isoformat(),
            "currency": "NGN",
            "total_amount": order.total_amount,
            "order_link": "#",
        }
        template = "buyer_order_confirmation.html"
        email_to = user.email
        subject = "Order Received"

        send_email_using_worker.delay(
            email_to=email_to,
            subject=subject,
            context=context,
            template_name=template,
        )

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Successfully proccessed order",
        )

    async def fetch_user_orders(
        self, user_id: str, db: AsyncSession, page: int = 1, page_size: int = 10
    ) -> dict[str, Any]:

        # Get paginated user order

        orders_data = await Order.fetch_user_orders(user_id, db, page, page_size)
        orders: list[Order] = orders_data["orders"]

        orders_dicts = []

        for order in orders:
            order_dict = order.to_dict()
            order_suborders = []

            suborders = order.suborders
            for suborder in suborders:
                suborder_dict = suborder.to_dict()
                order_items = suborder.order_items

                order_items_dicts = [order_item.to_dict() for order_item in order_items]

                suborder_dict["order_items"] = order_items_dicts

                order_suborders.append(suborder_dict)

            order_dict["suborders"] = order_suborders

            orders_dicts.append(order_dict)

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="successfully fetch user orders",
            data={
                "orders": orders_dicts,
                "page": orders_data["page"],
                "page_size": orders_data["page_size"],
                "total": orders_data["total"],
            },
        )

    async def fetch_user_order_by_id(
        self, order_id: str, db: AsyncSession
    ) -> dict[str, Any]:

        order = await Order.fetch_user_order_by_id(order_id, db)
        if not order:
            raise NotFoundException("Order not found")

        order_dict = order.to_dict()
        suborders = order.suborders
        suborder_dicts = []
        for suborder in suborders:
            suborder_dict = suborder.to_dict()

            order_items = suborder.order_items
            order_items_dict = [order_item.to_dict() for order_item in order_items]

            suborder_dict["order_items"] = order_items_dict
            suborder_dicts.append(suborder_dict)

        order_dict["suborders"] = suborder_dicts

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="successfully fetch order data",
            data=order_dict,
        )

    async def fetch_user_order_by_track_id(
        self, track_id: str, db: AsyncSession
    ) -> dict[str, Any]:

        order = await Order.fetch_user_order_by_track_id(track_id, db)
        if not order:
            raise NotFoundException("Order not found")

        order_dict = order.to_dict()
        suborders = order.suborders
        suborder_dicts = []
        for suborder in suborders:
            suborder_dict = suborder.to_dict()

            order_items = suborder.order_items
            order_items_dict = [order_item.to_dict() for order_item in order_items]

            suborder_dict["order_items"] = order_items_dict
            suborder_dicts.append(suborder_dict)

        order_dict["suborders"] = suborder_dicts

        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="successfully fetch order data",
            data=order_dict,
        )


order_service = OrderService()

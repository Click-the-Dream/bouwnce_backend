from datetime import UTC, datetime
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
from app.service.payment.paystack import paystack_service
from app.utils.exception import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    GoneException,
    InternalServerErrorException,
)
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
        self, user: User, redis: Redis, request: Request, db: AsyncSession
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

                # Compute the total ammount
                total_price = Order.compute_total_amount(reserved_product)

                payment_data = {
                    "email": user.email,
                    "amount": total_price * 100,  # convert to kobo
                }
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
                "products": [product.model_dump() for product in reserved_product],
                "idempotent_key": idempotent_key,
                "reference_token": referenceToken,
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

        products = order.products

        grouped_products_by_store = Order.group_products_by_store(products)

        # Create Suborders and order items
        for store_id, products_data in grouped_products_by_store.items():
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
            }
            suborder = await SubOrder.create(suborder_data, db)

            for product in products_data["products"]:
                order_item_data = {
                    "product_id": product.id,
                    "suborder_id": suborder.id,
                    "quantity": product.quantity,
                    "product_snapshot": {
                        "name": product.name,
                        "store_id": product.store_id,
                        "category": product.category,
                        "images": product.images,
                    },
                    "unit_price": product.amount,
                    "line_price": product.amount * product.quantity,
                }
                await OrderItem.create(order_item_data, db)

                # Decrease the stock and increase total sales of product (can be pushed to worker)
                await product_domain.decrease_product_stock_and_increase_total_sales(
                    product.id, product.quantity
                )

            # Release all the reserved products (can be pushed to worker)
            await Order.release_reserved_products(
                products_data["products"], str(user.id), redis
            )

            # update store's wallet (can be pushed to worker)
            await store.update_store_wallet(amount=products_data["total_amount"], db=db)

            # Send email to vendor for order
            now = datetime.now(UTC)
            year = now.year
            context = {
                "vendor_name": store.name,
                "username": user.username,
                "order_id": str(order.id),
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
            "order_id": str(order.id),
            "order_date": now.isoformat(),
            "currency": "NGN",
            "total_amount": order.total_amount,
            "order_link": "#",
            "item_preview": [],
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


order_service = OrderService()

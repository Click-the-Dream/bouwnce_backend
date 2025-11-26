from fastapi import status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.order import Order
from app.models.payment import Payment
from app.models.user import User
from app.service.payment.paystack import paystack_service
from app.utils.responses import response_builder


class OrderService:
    def __init__(self):
        self._max_tries = 10

    async def checkout(
        self, user: User, redis: Redis, idempotent_key: str, db: AsyncSession
    ) -> JSONResponse:
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
            carts = await Cart.get_by_user_id(user_id=str(user.id), db=db, all=True)

            # Check the  availability of the products in the carts
            avaialble_products, unavailable_products = (
                await Order.check_cart_availability(carts, redis)
            )

            # Reserve those available products
            reserved_product, cannot_reserve_products = await Order.reserve_products(
                avaialble_products, str(user.id), redis
            )

            # Add all the products that cannot be reserved to unvailable products
            unavailable_products.extend(cannot_reserve_products)

            # Compute the total ammount
            total_price = Order.compute_total_amount(reserved_product)

            payment_data = {
                "email": user.email,
                "amount": total_price * 100,  # convert to kobo
            }

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

                    return response_builder(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        status="error",
                        message="Error occured while creating payment intent",
                    )

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
                "products": reserved_product,
                "idemptotent_key": idempotent_key,
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

        except TypeError:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message="Invalid user Id",
            )

        except Exception as e:
            print("Error occured while checking user cart out: ", str(e))

            # Release all the reserved products
            try:
                await Order.release_reserved_products(
                    reserved_product, str(user.id), redis
                )
            except Exception as e:
                print("Error occured while releasing reserved products: ", str(e))

            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while checking out user cart",
            )

    async def handle_successful_payment(
        self, request: Request, db: AsyncSession
    ) -> JSONResponse:
        try:
            body = await request.body()

            data = body["data"]
            reference = data["reference"]
            order = await Order.get_by_reference(reference, db)

            if not order:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Invalid reference Token",
                )

            # The order status is not initiated or abandoned, then the order has been processed in one away or the other
            if order.status not in ["initiated", "abandoned"]:
                return response_builder(
                    status_code=status.HTTP_200_OK,
                    status="success",
                    message="Order has been processed",
                )

            if order.total_amount != data["amount"]:
                return response_builder(
                    status_code=status.HTTP_409_CONFLICT,
                    status="error",
                    message="amount mismatch",
                )

            products = order["products"]

            grouped_products_by_store = Order.group_products_by_store(products)
            print(grouped_products_by_store)

        except Exception as e:
            print("Error occured while handling order successul: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Internal server error",
            )

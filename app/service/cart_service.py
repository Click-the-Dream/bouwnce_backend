from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.products import product_domain
from app.schemas.cart import CartResponse, ProductResponse
from app.utils.responses import response_builder


class CartService:

    async def _formulate_response(self, cart: Cart) -> CartResponse:
        product = await product_domain.get_product_by_id(cart.product_id)
        product_response = ProductResponse(**product_domain.to_dict(product))
        cart_response = CartResponse(
            id=cart.id,
            user_id=cart.user_id,
            product=product_response,
            quantity=cart.quantity,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
        )
        return cart_response

    async def create(self, cart_data: dict[str, Any], db: AsyncSession) -> CartResponse:
        try:
            product = await product_domain.get_product_by_id(cart_data["product_id"])
            new_cart = await Cart.create(cart_data, db)

            product_response = ProductResponse(**product_domain.to_dict(product))
            cart_response = CartResponse(
                id=new_cart.id,
                user_id=new_cart.user_id,
                product=product_response,
                quantity=new_cart.quantity,
                created_at=new_cart.created_at,
                updated_at=new_cart.updated_at,
            )
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="product has been added to cart successfully",
                data=cart_response,
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except TypeError as te:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST, status="error", message=str(te)
            )
        except Exception as e:
            print("Error occured while creating a new cart: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occurred while creating cart",
            )

    async def get_all_by_user(
        self,
        user_id: str,
        db: AsyncSession,
        page: int | None = 1,
        page_size: int | None = 10,
    ) -> list[CartResponse]:

        try:
            user_carts = await Cart.get_by_user_id(user_id, db, page, page_size)

            cart_responses = []
            for cart in user_carts["data"]:
                cart_response = await self._formulate_response(cart)
                cart_responses.append(cart_response)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrieved user carts",
                data={
                    "carts": cart_responses,
                    "total": user_carts["total"],
                    "page": user_carts["page"],
                    "page_size": user_carts["page_size"],
                },
            )
        except TypeError as te:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST, status="error", message=str(te)
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except Exception as e:
            print("Error occured while retrieving cart data: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while retrieving cart data",
            )

    async def get_by_id(self, id: str, db: AsyncSession) -> CartResponse:
        try:
            cart = await Cart.get_by_id(id, db)
            if not cart:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="cart not found",
                )
            cart_response = await self._formulate_response(cart)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully retrieved cart details",
                data=cart_response,
            )
        except Exception as e:
            print("Error occurred while retrieving cart: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while retrieving cart data",
            )

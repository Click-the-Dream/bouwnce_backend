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

        cart_dict = cart.to_dict()
        cart_dict["user_id"] = str(cart.user_id)
        cart_dict["product"] = product_response
        cart_response = CartResponse(**cart_dict)

        return cart_response

    async def create(self, cart_data: dict[str, Any], db: AsyncSession) -> CartResponse:
        try:
            product = await product_domain.get_product_by_id(cart_data["product_id"])
            new_cart = await Cart.create(cart_data, db)

            product_response = ProductResponse(**product_domain.to_dict(product))

            new_data_dict = new_cart.to_dict()
            new_data_dict["product"] = product_response
            new_data_dict["user_id"] = str(new_cart.user_id)
            cart_response = CartResponse(**new_data_dict)

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
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except TypeError as te:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST, status="error", message=str(te)
            )
        except Exception as e:
            print("Error occurred while retrieving cart: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while retrieving cart data",
            )

    async def update(
        self, user_id: str, cart_id: str, update_data: dict[str, Any], db: AsyncSession
    ) -> CartResponse:
        try:
            cart = await Cart.get_by_id(cart_id, db)
            if cart.user_id != user_id:
                return response_builder(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="error",
                    message="You can't update someone else cart",
                )

            updated_cart = await Cart.update_by_id(cart_id, update_data, db)
            cart_response = await self._formulate_response(updated_cart)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully updated cart data",
                data=cart_response,
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
            print("Error occurred while updating cart data: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while updating cart",
            )

    async def delete(self, user_id: str, cart_id: str, db: AsyncSession):
        try:
            # This implementation can still be reduced to only a single query
            cart = await Cart.get_by_id(cart_id, db)
            if cart.user_id != user_id:
                return response_builder(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="error",
                    message="You cannot delete someone else cart",
                )

            await cart.delete(db)

            return response_builder(
                status_code=status.HTTP_200_OK, status="success", message="Deleted cart"
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
            print("Error deleting cart by id: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured deleting cart",
            )

    async def delete_all_user_cart(self, user_id: str, db: AsyncSession):
        try:
            await Cart.delete_by_user_id(user_id, db)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully deleted user carts",
            )
        except Exception as e:
            print("Error occured while deleting user cart: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while deleting user cart",
            )


cart_service = CartService()

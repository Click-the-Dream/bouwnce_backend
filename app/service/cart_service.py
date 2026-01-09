from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import Cart
from app.models.products import product_domain
from app.schemas.cart import CartResponse, PaginatedCartResponse
from app.utils.exception import (
    BadRequestException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.responses import response_builder


class CartService:

    async def _formulate_response(self, cart: Cart) -> dict[str, Any]:
        product = await product_domain.get_product_by_id(cart.product_id)
        if not product:
            raise ValueError("Product with Id not found")

        product_response = await product_domain.to_dict(product)

        cart_dict = cart.to_dict()
        cart_dict["user_id"] = str(cart.user_id)
        cart_dict["product"] = product_response

        return cart_dict

    async def create(self, cart_data: dict[str, Any], db: AsyncSession) -> CartResponse:
        try:
            product = await product_domain.get_product_by_id(cart_data["product_id"])
            if not product:
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="Product with id not found",
                )

            cart = await Cart.get_product_in_user_cart(
                cart_data["user_id"], cart_data["product_id"], db
            )
            if cart:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Product already in cart",
                )

            new_cart = await Cart.create(cart_data, db)

            product_response = await product_domain.to_dict(product)

            new_data_dict = new_cart.to_dict()
            new_data_dict["product"] = product_response
            new_data_dict["user_id"] = str(new_cart.user_id)

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="product has been added to cart successfully",
                data=new_data_dict,
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None
        except Exception as e:
            print("Error occured while creating a new cart: ", str(e))
            raise InternalServerErrorException(
                message="Error occurred while creating cart"
            ) from None

    async def get_all_by_user(
        self,
        user_id: str,
        db: AsyncSession,
        page: int | None = 1,
        page_size: int | None = 10,
    ) -> PaginatedCartResponse:

        try:
            user_carts = await Cart.get_by_user_id(user_id, db, page, page_size)

            cart_responses = []

            for cart in user_carts["data"]:
                try:
                    cart_response = await self._formulate_response(cart)
                    cart_responses.append(cart_response)
                except ValueError:
                    pass

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
            raise BadRequestException(message=str(te)) from None
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None
        except Exception as e:
            print("Error occured while retrieving cart data: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while retrieving cart data"
            ) from None

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
            raise NotFoundException(message=str(ve)) from None
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None
        except Exception as e:
            print("Error occurred while retrieving cart: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while retrieving cart data"
            ) from None

    async def update(
        self, user_id: str, cart_id: str, update_data: dict[str, Any], db: AsyncSession
    ) -> CartResponse:
        try:
            cart = await Cart.get_by_id(cart_id, db)
            if cart.user_id != user_id:
                raise ForbiddenException(message="You can't update someone else cart")

            updated_cart = await Cart.update_by_id(cart_id, update_data, db)
            cart_response = await self._formulate_response(updated_cart)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully updated cart data",
                data=cart_response,
            )
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None
        except Exception as e:
            print("Error occurred while updating cart data: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while updating cart"
            ) from None

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
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Deleted cart",
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None
        except Exception as e:
            print("Error deleting cart by id: ", str(e))
            raise InternalServerErrorException(
                message="Error occured deleting cart"
            ) from None

    async def delete_all_user_cart(self, user_id: str, db: AsyncSession):
        try:
            await Cart.delete_by_user_id(user_id, db)

            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="Successfully deleted user carts",
            )
        except Exception as e:
            print("Error occured while deleting user cart: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while deleting user cart"
            ) from None


cart_service = CartService()

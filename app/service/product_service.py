from typing import Any

from fastapi import UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Inventory
from app.models.products import product_domain
from app.utils.cloudinary_utils import cleanup_temp_files, save_uploaded_file_temp
from app.utils.exception import (
    BadRequestException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
)
from app.utils.responses import response_builder


class ProductService:
    async def create_product(
        self,
        store_id: str,
        product_data: dict[str, Any],
        images: list[UploadFile],
        db: AsyncSession,
    ) -> dict[str, Any]:
        try:
            if not images or len(images) == 0:
                raise BadRequestException(
                    message="Product image is required to create a product"
                )

            product_data["image_paths"] = await save_uploaded_file_temp(images)

            product = await product_domain.create_product(product_data, store_id)

            await cleanup_temp_files(product_data["image_paths"])

            # Create invontory row
            inventory_data = {
                "product_id": str(product.id),
                "available": product.stock,
                "reserved": 0,
            }
            await Inventory.create(inventory_data, db)

            product_response = await product_domain.to_dict(product)

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="successfuly created a new product",
                data=product_response,
            )
        except ValueError as ve:
            raise BadRequestException(
                message=f"Error creating product: {str(ve)}"
            ) from None

    async def get_product_by_id(self, product_id: str, redis: Redis) -> dict[str, Any]:

        try:

            product = await product_domain.get_product_by_id(product_id)
            if product.state != "live":
                raise NotFoundException(message="product with specified ID not found")

            product_response = await product_domain.to_dict(product, redis)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrieved a product",
                data=product_response,
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None

        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def get_products_by_store(
        self,
        store_id: str,
        redis: Redis,
        name: str | None = None,
        category: str | None = None,
        page: int | None = 1,
        per_page: int | None = 10,
    ) -> dict[str, Any]:
        try:
            filter = {}

            if name:
                filter["name"] = name

            if category:
                filter["category"] = category

            products_data = await product_domain.get_all_product_by_store(
                store_id, filter=filter, page=page, per_page=per_page
            )

            products = await product_domain.serialize_products(
                products_data["products"], redis
            )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrieve all product for a vendor",
                data={
                    "products": products,
                    "total": products_data["total"],
                    "page": products_data["page"],
                    "page_size": products_data["per_page"],
                },
            )
        except Exception as e:
            print("Error occured while fetching all product for vendor: ", str(e))
            raise InternalServerErrorException(
                message="Error occurred while fetching all vendor products"
            ) from None

    async def get_products(
        self,
        redis: Redis,
        product_name: str | None = None,
        produdct_category: str | None = None,
        page: int | None = 1,
        per_page: int | None = 10,
    ) -> dict[str, Any]:
        filter_dict = {}

        if product_name:
            filter_dict["name"] = product_name

        if produdct_category:
            filter_dict["category"] = produdct_category

        try:
            product_data = await product_domain.get_products_by(
                filter_dict, page=page, per_page=per_page
            )

            products = await product_domain.serialize_products(
                product_data["products"], redis
            )

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrieve all product for a vendor",
                data={
                    "products": products,
                    "total": product_data["total"],
                    "page": product_data["page"],
                    "page_size": product_data["per_page"],
                },
            )
        except Exception as e:
            print(f"Error occurred while fetching products: {str(e)}")
            raise InternalServerErrorException(
                message="Error occurred while fetching products"
            ) from None

    async def update_products(
        self,
        update_data: dict[str, Any],
        product_id: str,
        store_id: str,
        redis: Redis,
        images: list[UploadFile] | None = None,
    ) -> dict[str, Any]:

        try:
            product = await product_domain.get_product_by_id(product_id)
            if product.store_id != store_id:
                raise ForbiddenException(message="Product doesn't belong to this store")

            product = await product_domain.update_product(update_data, product_id)

            if images and len(images) > 0:
                temp_paths = await save_uploaded_file_temp(images)
                product = await product_domain.update_product_image(
                    product_id, temp_paths, store_id
                )
                await cleanup_temp_files(temp_paths)

            product_response = await product_domain.to_dict(product, redis)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Sucessfull updated product",
                data=product_response,
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def toggle_current_store_product_state(
        self, store_id: str, product_id: str
    ) -> dict[str, Any]:
        try:
            product = await product_domain.get_product_by_id(product_id)

            if product.store_id != str(store_id):
                raise ForbiddenException(
                    message="Product doesn't belong the this store"
                )

            state = product.state
            product.state = "live" if product.state == "draft" else "draft"

            if state == "live":
                message = "successfully toggle product state from live to draft"
            else:
                message = "successfully toggle product state from draft to live"

            await product.save()
            return response_builder(
                status_code=status.HTTP_200_OK, status="error", message=message
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None

        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def delete_products_by_id(
        self, product_id: str, store_id: str
    ) -> dict[str, Any]:
        try:
            product = await product_domain.get_product_by_id(product_id)
            if product.store_id != store_id:
                raise ForbiddenException(
                    message="Store cannot delete someone else product"
                )

            is_deleted = await product_domain.delete_product(product_id)
            if is_deleted:
                return response_builder(
                    status_code=status.HTTP_204_NO_CONTENT,
                    status="success",
                    message="successfully deleted product",
                )
            else:
                raise InternalServerErrorException(message="cannot delete product")

        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None

        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def delete_all_store_products(self, store_id: str) -> dict[str, Any]:
        try:
            deleted_count = await product_domain.delete_all_store_products(store_id)

            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="successfully deleted all vendor products",
                data={"product_deleted_count": deleted_count},
            )

        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None

    async def delete_product_image(
        self, product_id: str, image_public_id: str, store_id: str, redis: Redis
    ) -> dict[str, Any]:
        try:

            product = await product_domain.get_product_by_id(product_id)
            if product.store_id != store_id:
                raise ForbiddenException(
                    message="You cannot delete someone else product image"
                )

            product = await product_domain.delete_product_image(
                product_id, image_public_id
            )
            product_response = await product_domain.to_dict(product, redis)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="successfully deleted product image",
                data=product_response,
            )
        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None

        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

    async def get_product_categories(self) -> dict[str, Any]:
        try:
            categories = await product_domain.get_all_category()
            categories_response = [
                await product_domain.to_dict(category) for category in categories
            ]
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully get all available product categories",
                data=categories_response,
            )
        except Exception as e:
            print("Error retrieving product categories: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while fetching product categories"
            ) from None

    async def create_product_category(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            category = await product_domain.create_category(
                data["name"], data["description"]
            )
            category_response = await product_domain.to_dict(category)
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Successfully created a category",
                data=category_response,
            )
        except Exception as e:
            print("Error occurred while creating category: ", str(e))
            raise InternalServerErrorException(
                message="Error occured while creating a category"
            ) from None

    async def delete_product_category(self, id: str) -> dict[str, Any]:
        try:
            await product_domain.delete_category(id)
            return response_builder(
                status_code=status.HTTP_204_NO_CONTENT,
                status="success",
                message="successfully deleted category",
            )
        except TypeError as te:
            raise BadRequestException(message=str(te)) from None

        except ValueError as ve:
            raise NotFoundException(message=str(ve)) from None


product_service = ProductService()

from typing import Any

from fastapi import UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Inventory
from app.models.products import product_domain
from app.schemas.product import CategoryResponse, ProductResponse
from app.utils.cloudinary_utils import cleanup_temp_files, save_uploaded_file_temp
from app.utils.responses import response_builder


class ProductService:
    async def create_product(
        self,
        store_id: str,
        product_data: dict[str, Any],
        images: list[UploadFile],
        db: AsyncSession,
    ) -> ProductResponse:
        try:
            if not images or len(images) == 0:
                return response_builder(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    status="error",
                    message="Product image is required to create a product",
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

            product_response = ProductResponse(**product_domain.to_dict(product))

            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="successfuly created a new product",
                data=product_response,
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST,
                status="error",
                message=f"Error creating product: {str(ve)}",
            )
        except Exception as e:
            print("Error occured creating a product: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while creating product",
            )

    async def get_product_by_id(self, product_id: str) -> ProductResponse:

        try:
            product = await product_domain.get_product_by_id(product_id)

            if product.state != "live" or product.status != "active":
                return response_builder(
                    status_code=status.HTTP_404_NOT_FOUND,
                    status="error",
                    message="product with specified ID not found",
                )

            product_resposne = ProductResponse(**product_domain.to_dict(product))

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrieved a product",
                data=product_resposne,
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
            print("Error occured while fetching product by id: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching product",
            )

    async def get_products_by_store(
        self,
        store_id: str,
        name: str | None = None,
        category: str | None = None,
        page: int | None = 1,
        per_page: int | None = 10,
    ) -> list[ProductResponse]:
        try:
            filter = {"state": "live", "status": "active"}

            if name:
                filter["name"] = name

            if category:
                filter["category"] = category

            products_data = await product_domain.get_all_product_by_store(
                store_id, filter=filter, page=page, per_page=per_page
            )
            products = [
                ProductResponse(**product_domain.to_dict(product))
                for product in products_data["products"]
            ]

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrieve all product for a vendor",
                data={
                    "products": products,
                    "total": products_data["total"],
                    "page": products_data["page"],
                    "per_page": products_data["per_page"],
                },
            )
        except Exception as e:
            print("Error occured while fetching all product for vendor: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occurred while fetching all vendor products",
            )

    async def get_products(
        self,
        product_name: str | None = None,
        produdct_category: str | None = None,
        page: int | None = 1,
        per_page: int | None = 10,
    ) -> list[ProductResponse]:
        filter_dict = {"state": "live", "status": "active"}

        if product_name:
            filter_dict["name"] = product_name

        if produdct_category:
            filter_dict["category"] = produdct_category

        try:
            product_data = await product_domain.get_products_by(
                filter_dict, page=page, per_page=per_page
            )
            products = [
                ProductResponse(**product_domain.to_dict(product))
                for product in product_data["products"]
            ]
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully retrieve all product for a vendor",
                data={
                    "products": products,
                    "total": product_data["total"],
                    "page": product_data["page"],
                    "per_page": product_data["per_page"],
                },
            )
        except Exception as e:
            print(
                f"Error occurred while fetching products ValueErrorby filtering: {str(e)}"
            )
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occurred while fetching products",
            )

    async def update_products(
        self,
        update_data: dict[str, Any],
        product_id: str,
        store_id: str,
        images: list[UploadFile] | None = None,
    ) -> ProductResponse:

        try:
            product = await product_domain.get_product_by_id(product_id)
            if product.store_id != store_id:
                return response_builder(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="error",
                    message="Product doesn't belong to this store",
                )

            product = await product_domain.update_product(update_data, product_id)

            if images and len(images) > 0:
                temp_paths = await save_uploaded_file_temp(images)
                product = await product_domain.update_product_image(
                    product_id, temp_paths, store_id
                )
                await cleanup_temp_files(temp_paths)

            product_response = ProductResponse(**product_domain.to_dict(product))
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
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST, status="error", message=str(te)
            )
        except Exception as e:
            print("Error updating product: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occurred while updating product",
            )

    async def toggle_current_store_product_state(
        self, store_id: str, product_id: str
    ) -> ProductResponse:
        try:
            product = await product_domain.get_product_by_id(product_id)
            if product.store_id != store_id:
                return response_builder(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="error",
                    message="Product doesn't below the this store",
                )

            state = product.state
            product.state = "active" if product.state == "draft" else "draft"

            if state == "active":
                message = "successfully toggle product state from active to draft"
            else:
                message = "successfully toggle product state from draft to active"

            await product.save()
            return response_builder(
                status_code=status.HTTP_200_OK, status="error", message=message
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
            print("Error occured while toggling product state: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while toggling product state",
            )

    async def delete_products_by_id(self, product_id: str, store_id: str):
        try:
            product = await product_domain.get_product_by_id(product_id)
            if product.store_id != store_id:
                return response_builder(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="error",
                    message="Store cannot delete someone else product",
                )

            is_deleted = await product_domain.delete_product(product_id)
            if is_deleted:
                return response_builder(
                    status_code=status.HTTP_200_OK,
                    status="success",
                    message="successfully deleted product",
                )
            else:
                return response_builder(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    status="error",
                    message="cannot delete product",
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
            print("Error occured while deleting product: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="errro",
                message="Error occured while deleting product",
            )

    async def delete_all_store_products(self, store_id: str):
        try:
            deleted_count = await product_domain.delete_all_store_products(store_id)

            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully deleted all vendor products",
                data={"product_deleted_count": deleted_count},
            )

        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except Exception as e:
            print("Error occured while deleting all vendor's producs: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occurred while deleting all vendor's products",
            )

    async def delete_product_image(
        self, product_id: str, image_public_id: str, store_id: str
    ) -> ProductResponse:
        try:

            product = await product_domain.get_product_by_id(product_id)
            if product.store_id != store_id:
                return response_builder(
                    status_code=status.HTTP_403_FORBIDDEN,
                    status="error",
                    message="You cannot delete someone else product image",
                )

            product = await product_domain.delete_product_image(
                product_id, image_public_id
            )
            product_response = ProductResponse(**product_domain.to_dict(product))
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully deleted product image",
                data=product_response,
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
            print("Error occurred while deleting image product: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while deleting image product",
            )

    async def get_product_categories(self):
        try:
            categories = await product_domain.get_all_category()
            categories_response = [
                CategoryResponse(**product_domain.to_dict(category))
                for category in categories
            ]
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Successfully get all available product categories",
                data=categories_response,
            )
        except Exception as e:
            print("Error retrieving product categories: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while fetching product categories",
            )

    async def create_product_category(self, data: dict[str, Any]) -> CategoryResponse:
        try:
            category = await product_domain.create_category(
                data["name"], data["description"]
            )
            category_response = CategoryResponse(**product_domain.to_dict(category))
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Successfully created a category",
                data=category_response,
            )
        except Exception as e:
            print("Error occurred while creating category: ", str(e))
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while creating a category",
            )

    async def delete_product_category(self, id: str) -> CategoryResponse:
        try:
            await product_domain.delete_category(id)
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="successfully deleted category",
            )
        except TypeError as te:
            return response_builder(
                status_code=status.HTTP_400_BAD_REQUEST, status="error", message=str(te)
            )
        except ValueError as ve:
            return response_builder(
                status_code=status.HTTP_404_NOT_FOUND, status="error", message=str(ve)
            )
        except Exception:
            print("Error occured while deleting product category")
            return response_builder(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                status="error",
                message="Error occured while deleting product category",
            )


product_service = ProductService()

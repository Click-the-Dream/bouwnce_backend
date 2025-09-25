from typing import Annotated, Any

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base_document import BaseDocument
from app.utils.cloudinary_utils import delete_folder, delete_images, upload_images


class Images(BaseModel):
    url: str
    public_id: str


class Category(BaseDocument):
    name: Annotated[str, Field(min_length=3, max_length=20)]
    description: str | None

    class Settings:
        name = "categories"


class Product(BaseDocument):
    vendor_id: str
    name: Annotated[str, Field(min_length=3, max_length=50)]
    description: str | None
    amount: Annotated[int, Field(ge=0)]
    stock: Annotated[int, Field(ge=0)]
    category: str
    status: str
    images: list[Images]

    class Settings:
        name = "products"


class ProductDomain:

    def __init__(self):
        self.Product = Product
        self.Category = Category

    def to_dict(self, obj) -> dict[str, Any]:
        obj_dict = obj.__dict__.copy()

        if obj_dict.get("_sa_instance_state"):
            obj_dict.pop("_sa_instance_state")

        if obj_dict.get("revision_id"):
            obj_dict.pop("revision_id")

        obj_dict["id"] = str(obj.id)
        obj_dict["created_at"] = obj.created_at.isoformat()
        obj_dict["updated_at"] = obj.updated_at.isoformat()

        return obj_dict

    async def create_product(self, data: dict[str, Any], vendor_id: str) -> Product:
        try:
            product_category = data["category"]
            category = await self.get_category_name(product_category)

            if not category:
                raise ValueError("Invalid category name")

            image_paths = data["image_paths"]
            status = "draft"

            data["status"] = status

            image_results = await upload_images(image_paths, vendor_id)
            images = [
                Images(url=image["url"], public_id=image["public_id"])
                for image in image_results
                if image is not None
            ]

            product = self.Product(
                vendor_id=vendor_id,
                name=data["name"],
                description=data["description"],
                amount=int(data["amount"]),
                stock=int(data["stock"]),
                category=category.name,
                status=status,
                images=images,
            )

            await product.insert()
            return product
        except Exception as e:
            print(f"Error occured creating a new product: {str(e)}")
            return None

    async def get_category_name(self, name: str) -> Category:
        query = {"name": {"$regex": f".*{name}.*", "$options": "i"}}

        category = await self.Category.find_one(query)
        if not category:
            raise ValueError(f"Category with {name} not specified")

        return category

    async def delete_category(self, id: str) -> bool:

        try:
            PydanticObjectId(id)
        except Exception as e:
            raise TypeError(str(e)) from None

        category = await self.Category.find_one(Category.id == PydanticObjectId(id))
        if not category:
            raise ValueError(f"Category with id {id} not found")

        await category.delete()

        return True

    async def create_category(self, name: str, description: str) -> Category:

        try:
            query = {"name": {"$regex": f".*{name}.*", "$options": "i"}}

            category = await self.Category.find_one(query)
            if category:
                return category

            category = self.Category(name=name, description=description)
            await category.insert()
            return category
        except Exception as e:
            print(f"Error saving {name} category: ", str(e))
            return None

    async def get_all_category(self) -> list[Category]:

        categories = await self.Category.find_all().to_list()

        return categories

    async def get_all_product_by_vendor(
        self,
        vendor_id: str,
        filter: dict[str, Any],
        page: int = 1,
        per_page: int = 10,
    ) -> list[Product]:
        offset = (page - 1) * per_page
        query = []

        for key, value in filter.items():
            if hasattr(self.Product, key):
                regrex = {"$regex": f".*{value}.*", "$options": "i"}
                query.append({key: regrex})

        if len(query) > 0:
            filters = {"$and": [{"vendor_id": vendor_id}, {"$or": query}]}
            products_query = self.Product.find(filters).sort(-self.Product.updated_at)
        else:
            products_query = self.Product.find(
                self.Product.vendor_id == vendor_id
            ).sort(-self.Product.updated_at)

        count = await products_query.count()
        products = await products_query.skip(offset).limit(per_page).to_list()
        return {
            "products": products,
            "total": count,
            "page": page,
            "per_page": per_page,
        }

    async def get_products_by(
        self,
        filter: dict[str, Any],
        page: int | None = 1,
        per_page: int | None = 10,
    ) -> list[Product]:

        query = []

        for key, value in filter.items():
            if hasattr(self.Product, key):
                regrex = {"$regex": f".*{value}.*", "$options": "i"}
                query.append({key: regrex})
        if len(query) > 0:
            results_query = self.Product.find({"$or": query}).sort(
                -self.Product.updated_at
            )
        else:
            results_query = self.Product.find().sort(-self.Product.updated_at)
        offset = (page - 1) * per_page
        count = await results_query.count()
        results = await results_query.skip(offset).limit(per_page).to_list()
        return {"products": results, "total": count, "page": page, "per_page": per_page}

    async def get_product_by_id(self, id: str) -> Product:
        try:
            PydanticObjectId(id)
        except Exception as e:
            raise TypeError(str(e)) from None

        product = await self.Product.find_one(self.Product.id == PydanticObjectId(id))
        if not product:
            raise ValueError(f"product with product id {id} not found")
        return product

    async def update_product(self, data: dict[str, Any], product_id: str) -> Product:

        product = await self.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with {product_id} not found")

        exclude_key = ["id", "created_at", "updated_at"]
        for key, value in data.items():
            if hasattr(product, key) and key not in exclude_key:
                setattr(product, key, value)

        await product.save()

        return product

    async def delete_product_image(
        self, product_id: str, image_public_id: str
    ) -> Product:

        product = await self.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with {product_id} not found")

        for image in product.images:
            if image.public_id == image_public_id:
                result = delete_images([image_public_id])

                if not result:
                    raise Exception(
                        f"Unable to delete image with {image_public_id} public_id"
                    )

                product.images.remove(image)
                await product.save()
                return product

        raise ValueError(f"there is no image with {image_public_id} publid id")

    async def update_product_image(
        self, product_id: str, image_paths: list[str], vendor_id
    ) -> Product:

        product = await self.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with {product_id} not found")

        image_result = await upload_images(image_paths, vendor_id)
        images = [
            Images(url=image["url"], public_id=image["public_id"])
            for image in image_result
            if image is not None
        ]

        if product.images and len(product.images) > 0:
            product.images.extend(images)
        else:
            product.images = images

        await product.save()

        return product

    async def delete_product(self, product_id: str) -> bool:

        product = await self.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with {product_id} not found")

        if product.images and len(product.images) > 0:
            image_public_ids = [image.public_id for image in product.images]
            result = delete_images(image_public_ids)
            if not result:
                raise Exception(f"Error delete product with product id {product_id}")

        await product.delete()
        return True

    async def delete_all_vendor_products(self, vendor_id: str) -> bool:

        result = delete_folder(vendor_id)
        if not result:
            raise Exception(
                f"Error delete products of vendor with vendor_id {vendor_id}"
            )

        result = await self.Product.find(self.Product.vendor_id == vendor_id).delete()

        return result.deleted_count


product_domain = ProductDomain()

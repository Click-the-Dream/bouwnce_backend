import asyncio
from time import time
from typing import Annotated, Any

from beanie.operators import Eq, In
from bson import ObjectId
from pydantic import BaseModel, Field
from redis.asyncio import Redis, WatchError

from app.core.config import settings
from app.models.base_document import BaseDocument
from app.utils.cloudinary_utils import delete_folder, delete_images, upload_images


class Images(BaseModel):
    public_id: Annotated[
        str, Field(examples=["a0e43d-1ccc-4370-a32e-41812280b26e/zjejpt55jhouwwwplllo"])
    ]
    url: Annotated[str, Field(examples=["http://image_url.png"])]




class Category(BaseDocument):
    name: Annotated[str, Field(min_length=3, max_length=20)]
    description: str | None

    class Settings:
        name = "categories"


class Product(BaseDocument):
    store_id: str
    name: Annotated[str, Field(min_length=3, max_length=50)]
    description: str | None
    amount: Annotated[int, Field(ge=0)]
    stock: Annotated[int, Field(ge=0)]
    category: str
    state: str
    images: list[Images]
    status: str
    total_sales: Annotated[int, Field(default=0)]

    class Settings:
        name = "products"


class ProductDomain:

    def __init__(self):
        self.Product = Product
        self.Category = Category
        self._max_tries = 5

    def _compute_reserved_product_key(self, product_id: str) -> str:
        """Return a redis key used to store reserved product stock"""
        return f"reserved:product:{product_id}"

    def _compute_reserved_product_user_key(self, product_id: str, user_id: str) -> str:
        """Return a redis key used to store reserved product stock of a user"""
        return f"reserved:product:{product_id}:{user_id}"

    async def get_available_product_stock(self, obj: Product, redis: Redis) -> int:
        """Check if a product is still available by checking against reserve stock"""

        if obj.stock <= 0:
            return 0

        redis_key = self._compute_reserved_product_key(str(obj.id))
        reserved_stock = await redis.get(redis_key)
        if reserved_stock is None:
            return obj.stock
        
        avaialble = obj.stock - int(reserved_stock)
        return max(avaialble, 0)

    async def reserve_product(
        self,
        product_id: str,
        user_id: str,
        quantity: int,
        available_quantity: int,
        redis: Redis,
    ) -> tuple[bool, str | None]:
        """Reserve stock by adding to temporarily adding to redis"""
        product_key = self._compute_reserved_product_key(product_id)
        product_user_key = self._compute_reserved_product_user_key(product_id, user_id)

        async with redis.pipeline() as pipe:
            for attempt in range(self._max_tries):
                try:
                    await pipe.watch(product_key)

                    currently_reserved_prod = int(await pipe.get(product_key) or 0)
                    user_reserved = await pipe.get(product_user_key)

                    if currently_reserved_prod + quantity > available_quantity:
                        await pipe.unwatch()
                        return False, "Not enough available quantity"

                    # Multiple Execution for atomic transaction
                    now = time() + int(settings.RESERVATION_TTL)

                    pipe.multi()

                    # If user has already reserved product before
                    # Decrease the quantity reserved before from product
                    # Before increasing with this new quantity
                    if user_reserved is not None:
                        user_reserved = int(user_reserved or 0)
                        pipe.decrby(product_key, user_reserved)

                    pipe.incrby(product_key, quantity)
                    pipe.set(product_user_key, quantity)
                    pipe.zadd("reservation_expiries", {product_user_key: now})
                    await pipe.execute()

                    return True, None
                except WatchError:

                    # Retry if race condition occured
                    if attempt < self._max_tries - 1:
                        await asyncio.sleep(0.05)
                        continue
                    else:
                        return False, "Maximum WatchError reached"
                except Exception as e:

                    await pipe.unwatch()
                    raise e

            return False, "Error occured"

    async def release_product(self, product_id: str, user_id: str, redis: Redis):
        """Releases all the products that has been reserved"""

        product_key = self._compute_reserved_product_key(product_id)
        product_user_key = self._compute_reserved_product_user_key(product_id, user_id)
        zset_key = "reservation_expires"

        for attempt in range(self._max_tries):
            try:
                async with redis.pipeline() as pipe:

                    # Prevent Race Condition
                    await pipe.watch(product_key, product_user_key)

                    quantity = int(await pipe.get(product_user_key) or 0)

                    if quantity == 0:
                        await pipe.unwatch()
                        return True  # There is nothing to release

                    pipe.multi()
                    pipe.delete(product_user_key)
                    pipe.decrby(product_key, quantity)
                    pipe.zrem(zset_key, product_user_key)

                    await pipe.execute()

                    return True
            except WatchError:

                if attempt < self._max_tries - 1:
                    await asyncio.sleep(0.05)
                    continue
                else:
                    await pipe.unwatch()
                    return False

            except Exception as e:
                await pipe.unwatch()
                raise e

    async def decrease_product_stock_and_increase_total_sales(
        self, product_id: str, quantity: int
    ) -> bool:
        self.Product.find(Product.id == ObjectId(product_id)).update(
            {"$inc": {"stock": (-quantity), "total_sales": quantity}}
        )
        return True

    async def to_dict(self, obj: Product, redis: Redis | None = None) -> dict[str, Any]:
        obj_dict = obj.__dict__.copy()

        if obj_dict.get("revision_id"):
            obj_dict.pop("revision_id")

        obj_dict["id"] = str(obj.id)
        obj_dict["created_at"] = obj.created_at.isoformat()
        obj_dict["updated_at"] = obj.updated_at.isoformat()

        if redis:
            obj_dict["stock"] = await self.get_available_product_stock(obj, redis)

        return obj_dict

    async def serialize_products(
        self, objs: list[Product], redis: Redis
    ) -> list[dict[str, Any]]:

        obj_key_list = []
        obj_dicts_list = []
        for obj in objs:
            obj_dict = obj.__dict__.copy()

            if obj_dict.get("revision_id"):
                obj_dict.pop("revision_id")

            obj_dict["id"] = str(obj.id)
            obj_dict["created_at"] = obj.created_at.isoformat()
            obj_dict["updated_at"] = obj.updated_at.isoformat()

            # Convert images to dict
            if obj.images:
                images = []
                for img in obj.images:
                    images.append(img.model_dump())

                obj_dict["images"] = images

            obj_dicts_list.append(obj_dict)
            obj_key_list.append(self._compute_reserved_product_key(str(obj.id)))

        reserved_stocks = await redis.mget(obj_key_list)

        for obj_dict, reserved_stock in zip(
            obj_dicts_list, reserved_stocks, strict=False
        ):
            stock = obj_dict.get("stock", 0)
            if reserved_stock is None:
                obj_dict["stock"] = stock
            else:
                available = stock - int(reserved_stock)
                obj_dict["stock"] = max(available, 0)

        return obj_dicts_list

    async def create_product(self, data: dict[str, Any], store_id: str) -> Product:

        product_category = data["category"]
        category = await self.get_category_name(product_category)

        image_paths = data["image_paths"]
        state = "draft"
        status = "active"

        data["state"] = state

        image_results = await upload_images(image_paths, store_id)
        images = [
            Images(url=image["url"], public_id=image["public_id"])
            for image in image_results
            if image is not None
        ]

        product = self.Product(
            store_id=store_id,
            name=data["name"],
            description=data["description"],
            amount=int(data["amount"]),
            stock=int(data["stock"]),
            category=category.name,
            state=state,
            status=status,
            images=images,
        )

        await product.insert()
        return product

    async def get_category_name(self, name: str) -> Category:
        query = {"name": {"$regex": f".*{name}.*", "$options": "i"}}

        category = await self.Category.find_one(query)
        if not category:
            raise ValueError(
                f"Invalid category name: {name}, pls check the category and try again"
            )

        return category

    async def delete_category(self, id: str) -> bool:

        if not ObjectId.is_valid(id):
            raise TypeError(f"Invalid product Id: {id}") from None

        category = await self.Category.find_one(Category.id == id)
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

    async def get_all_product_by_store(
        self,
        store_id: str,
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

            filters = {"$and": [{"store_id": store_id}, {"$or": query}]}
            products_query = self.Product.find(filters).sort(-self.Product.updated_at)

        else:

            products_query = self.Product.find(self.Product.store_id == store_id).sort(
                -self.Product.updated_at
            )

        count = await products_query.count()
        products = await products_query.skip(offset).limit(per_page).to_list()
        return {
            "products": products,
            "total": count,
            "page": page,
            "per_page": per_page,
        }

    async def get_products_by_ids(self, product_ids: list[str]) -> list[Product]:

        object_ids = []
        for id in product_ids:
            if not ObjectId.is_valid(id):
                raise TypeError(f"Invalid product id: {id}")

            object_ids.append(ObjectId(id))

        filter = [
            In(self.Product.id, object_ids),
            self.Product.state == "live",
            Eq(self.Product.status, "active"),
        ]
        products = await self.Product.find(*filter).to_list()

        return products

    async def get_products_by(
        self,
        filter: dict[str, Any],
        page: int | None = 1,
        per_page: int | None = 10,
    ) -> dict[str, Any]:

        query = []

        for key, value in filter.items():
            if hasattr(self.Product, key):
                regrex = {"$regex": f".*{value}.*", "$options": "i"}
                query.append({key: regrex})
        if len(query) > 0:
            print(query)
            results_query = self.Product.find(
                {"$and": [{"$or": query}, {"state": "live"}, {"status": "active"}]}
            ).sort(-self.Product.updated_at)
        else:
            results_query = self.Product.find({"state": "live", "status": "active"}).sort(
                -self.Product.updated_at
            )

        offset = (page - 1) * per_page
        count = await results_query.count()
        results = await results_query.skip(offset).limit(per_page).to_list()
        return {"products": results, "total": count, "page": page, "per_page": per_page}

    async def get_product_by_id(self, id: str) -> Product:
        if not ObjectId.is_valid(id):
            raise TypeError(f"Invalid product id: {id}") from None

        product = await self.Product.find_one(self.Product.id == ObjectId(id))
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

    async def deactivate_stores_products(self, store_id: str):

        products = await self.Product.find({"store_id": store_id}).update_many(
            {"$set": {"status": "inactive"}}
        )

        return bool(products)

    async def activate_stores_prouducts(self, store_id: str):
        products = await self.Product.find({"store_id": store_id}).update_many(
            {"$set": {"status": "active"}}
        )

        return bool(products)

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
        self, product_id: str, image_paths: list[str], store_id
    ) -> Product:

        product = await self.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with {product_id} not found")

        image_result = await upload_images(image_paths, store_id)
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

    async def delete_all_store_products(self, store_id: str) -> bool:

        result = delete_folder(store_id)
        if not result:
            raise Exception(f"Error delete products of vendor with store_id {store_id}")

        result = await self.Product.find(self.Product.store_id == store_id).delete()

        return result.deleted_count


product_domain = ProductDomain()

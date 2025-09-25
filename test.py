import asyncio

from app.db.mongo import mongo_conn
from app.models.products import ProductDomain

product_data = {
    "name": "Jeans",
    "description": "Straigth from New York",
    "amount": 25000,
    "stock": 25,
    "category": "clothes",
    "image_paths": [
        "test_products/women_baggy_jeans6.jpg",
        "test_products/women_baggy_jeans8.jpg",
        "test_products/women_polo1.jpeg",
    ],
}
vendor_id = "cd7369f3-5f04-4dd0-a8f4-9b3566867e13"


async def main():
    await mongo_conn()
    # category = await ProductDomain.create_category(name="clothes", description="This is clothes categories")
    # product = await ProductDomain.create_product(product_data, vendor_id)
    products = await ProductDomain.get_products_by({"name": "bag"})
    print(products)

    return True


asyncio.run(main())

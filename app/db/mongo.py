from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import errors

from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_DATABASE_URL)
db = client.get_database(settings.MONGODB_DB_NAME)


async def mongo_conn():
    from app.models.products import Category, Product

    try:
        await client.admin.command("ping")
        print("✅ MongoDB database connected successfully")
    except errors.ConnectionFailure as e:
        print("❌ Failed to connect to MongoDB")
        print(f"Error: {e}")

    await init_beanie(database=db, document_models=[Product, Category])
    return client

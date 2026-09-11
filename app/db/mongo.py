from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import errors

from app.core.config import settings

if not settings.MONGODB_DATABASE_URL:
    raise ValueError("MONGODB_DATABASE_URL is not set in the environment variables")

client = AsyncIOMotorClient(settings.MONGODB_DATABASE_URL)
db = client.get_database(settings.MONGODB_DB_NAME)


async def mongo_conn():
    from app.models.products import Category, Product
    from app.search_parser.model.parse_cache import SearchCatalogCache, SearchParseCache

    try:
        await client.admin.command("ping")
        print("✅ MongoDB database connected successfully")
    except errors.ConnectionFailure as e:
        print("❌ Failed to connect to MongoDB")
        print(f"Error: {e}")

    await init_beanie(
        database=db,
        document_models=[Product, Category, SearchParseCache, SearchCatalogCache],
    )
    return client

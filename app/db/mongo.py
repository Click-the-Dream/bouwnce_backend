from contextlib import contextmanager

from pymongo import MongoClient, errors

from app.core.config import settings

client = MongoClient(settings.MONGODB_DATABASE_URL)

try:
    client.admin.command("ping")
    print("✅ MongoDB database connected successfully")
except errors.ConnectionFailure as e:
    print("❌ Failed to connect to MongoDB")
    print(f"Error: {e}")

db = client.get_database(settings.MONGODB_DB_NAME)


@contextmanager
def mongo_session():
    session = client.start_session()
    try:
        session.start_transaction()
        yield db, session
        session.commit_transaction()
    except Exception as e:
        session.abort_transaction()
        raise e
    finally:
        session.end_session()

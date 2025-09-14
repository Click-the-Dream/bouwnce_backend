from app.db.mongo import mongo_session
from app.db.postgres import SessionLocal
from app.db.redis import redis_client


def get_postgres_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_mongo_db():
    with mongo_session() as (database, session):
        yield database, session


def get_redis():
    try:
        yield redis_client
    finally:
        pass

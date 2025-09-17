import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import config_options
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from contextlib import asynccontextmanager
from fastapi import FastAPI


env = os.getenv("FASTAPI_ENV", "development")
settings = config_options[env]

Base = declarative_base()

DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL



if DATABASE_URL is None:
    raise ValueError("SQLALCHEMY_DATABASE_URL is not set in .env file")

try:
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.SQLALCHEMY_ECHO,
        future=settings.SQLALCHEMY_FUTURE,
        pool_size=int(settings.SQLALCHEMY_POOL_SIZE),
        max_overflow=int(settings.SQLALCHEMY_MAX_OVERFLOW),
    )
except OperationalError as e:
    print("Error connecting to the database:", e)
    raise

async_session = sessionmaker(autocommit=False, 
                             autoflush=False,
                             bind=engine,
                             class_=AsyncSession,
                             expire_on_commit=False
                             )


@asynccontextmanager
async def get_async_session():
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            print(f"Error during session: {e}")
            raise
        finally:
            await session.close()
            
def register_db_shutdown(app: FastAPI):
    @app.on_event("shutdown")
    async def shutdown_db():
        await engine.dispose()
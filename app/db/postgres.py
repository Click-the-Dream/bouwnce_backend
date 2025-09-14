from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.POSTGRES_DATABSE_URL)

try:
    with engine.connect() as conn:
        print("✅ PostgreSQL database connected successfully")
except OperationalError as e:
    print("❌ Failed to connect to PostgreSQL")
    print(f"Error: {e}")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

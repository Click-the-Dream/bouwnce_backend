from decouple import config
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    API_STR: str = config("API_STR", default="api/v1")

    POSTGRES_DATABSE_URL: str = config("POSTGRES_DATABSE_URL")
    MONGODB_DATABASE_URL: str = config("MONGODB_DATABASE_URL")
    MONGODB_DB_NAME: str = config("MONGODB_DB_NAME")
    REDIS_URL: str = config("REDIS_URL")

    SECRET_KEY: str = config("SECRET_KEY")

    PROJECT_NAME: str = config("PROJECT_NAME")


settings = Settings()

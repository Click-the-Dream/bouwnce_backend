from decouple import config
from pydantic import EmailStr
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

    ALGORITHM: str = config("ALGORITHM")

    SMTP_TLS: bool = config("SMTP_TLS")
    SMTP_SSL: bool = config("SMTP_SSL")
    SMTP_PORT: int = config("SMTP_PORT")
    SMTP_HOST: str | None = config("SMTP_HOST")
    SMTP_USER: str | None = config("SMTP_USER")
    SMTP_PASSWORD: str = config("SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: EmailStr = config("EMAILS_FROM_EMAIL")
    EMAILS_FROM_NAME: str = config("EMAILS_FROM_NAME")
    EmAIL_VERIFICATION_EXPIRE_MINUTES: int = config("EmAIL_VERIFICATION_EXPIRE_MINUTES")


settings = Settings()

from decouple import config
from pydantic import BaseModel, EmailStr


class Config(BaseModel):
    # Common settings
    API_STR: str = config("API_STR", default="api/v1")
    PORT: int = config("PORT", 8000, cast=int)

    SQLALCHEMY_DATABASE_URL: str

    MONGODB_DATABASE_URL: str = config("MONGODB_DATABASE_URL")
    MONGODB_DB_NAME: str = config("MONGODB_DB_NAME")

    RESEND_API_KEY: str = config("RESEND_API_KEY")
    RESEND_EMAIL: str = config("RESEND_EMAIL")
    REDIS_URL: str = config("REDIS_URL")
    SECRET_KEY: str = config("SECRET_KEY")
    PROJECT_NAME: str = config("PROJECT_NAME")

    ALGORITHM: str = config("ALGORITHM")

    SMTP_TLS: bool = config("SMTP_TLS", cast=bool)
    SMTP_SSL: bool = config("SMTP_SSL", cast=bool)
    SMTP_PORT: int = config("SMTP_PORT", cast=int)
    SMTP_HOST: str | None = config("SMTP_HOST")
    SMTP_USER: str | None = config("SMTP_USER")
    SMTP_PASSWORD: str = config("SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: EmailStr = config("EMAILS_FROM_EMAIL")
    EMAILS_FROM_NAME: str = config("EMAILS_FROM_NAME")
    CLOUDINARY_KEY: str = config("CLOUDINARY_KEY")
    CLOUDINARY_SECRET: str = config("CLOUDINARY_SECRET")
    CLOUDINARY_NAME: str = config("CLOUDINARY_NAME")
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = config("EMAIL_VERIFICATION_EXPIRE_MINUTES")


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_PROD_URL")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW")
    SQLALCHEMY_FUTURE: bool = config("SQLALCHEMY_FUTURE")
    SQLALCHEMY_ECHO: bool = config("SQLALCHEMY_ECHO")


class StagingConfig(Config):
    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_STAG_URL")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW")
    SQLALCHEMY_FUTURE: bool = True
    SQLALCHEMY_ECHO: bool = False


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_DEV_URL")
    SQLALCHEMY_FUTURE: bool = config("SQLALCHEMY_FUTURE")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW")
    SQLALCHEMY_ECHO: bool = False


environment = config("FASTAPI_ENV")

if environment == "production":
    settings = ProductionConfig()
elif environment == "staging":
    settings = StagingConfig()
else:
    print("Running in Development Environment")
    settings = DevelopmentConfig()

# Environment map
config_options = {
    "production": ProductionConfig(),
    "staging": StagingConfig(),
    "development": DevelopmentConfig(),
}

from decouple import config
from pydantic import BaseModel


class Config(BaseModel):
    # Common settings
    API_STR: str = config("API_STR", default="api/v1")

    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_URL")

    MONGODB_DATABASE_URL: str = config("MONGODB_DATABASE_URL")
    MONGODB_DB_NAME: str = config("MONGODB_DB_NAME")

    REDIS_HOST: str = config("REDIS_HOST")
    REDIS_PORT: int = config("REDIS_PORT", cast=int)
    REDIS_PASSWORD: str = config("REDIS_PASSWORD")
    REDIS_DB: int = config("REDIS_DB", cast=int)

    SECRET_KEY: str = config("SECRET_KEY")
    PROJECT_NAME: str = config("PROJECT_NAME")


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_PROD_URL")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE", cast=int)
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW", cast=int)
    SQLALCHEMY_FUTURE: bool = config("SQLALCHEMY_FUTURE", cast=bool)


class StagingConfig(Config):
    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_STAG_URL")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE", cast=int)
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW", cast=int)
    SQLALCHEMY_FUTURE: bool = config("SQLALCHEMY_FUTURE", cast=bool)


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_DEV_URL")
    SQLALCHEMY_FUTURE: bool = config("SQLALCHEMY_FUTURE", cast=bool)

    REDIS_HOST: str = config("REDIS_DEV_HOST")
    REDIS_PORT: int = config("REDIS_DEV_PORT", cast=int)
    REDIS_PASSWORD: str = config("REDIS_DEV_PASSWORD")
    REDIS_DB: int = config("REDIS_DEV_DB", cast=int)


# Environment map
config_options = {
    "production": ProductionConfig(),
    "staging": StagingConfig(),
    "development": DevelopmentConfig(),
}

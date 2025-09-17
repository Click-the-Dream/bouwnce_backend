from decouple import config
from pydantic import BaseModel


class Config(BaseModel):
    # Common settings
    API_STR: str = config("API_STR", default="api/v1")

    SQLALCHEMY_DATABASE_URL: str

    MONGODB_DATABASE_URL: str = config("MONGODB_DATABASE_URL")
    MONGODB_DB_NAME: str = config("MONGODB_DB_NAME")

    REDIS_URL: str = config("REDIS_URL")
    SECRET_KEY: str = config("SECRET_KEY")
    PROJECT_NAME: str = config("PROJECT_NAME")


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
    # REDIS_HOST: str = config("REDIS_DEV_HOST")
    # REDIS_PORT: int = config("REDIS_DEV_PORT")
    # REDIS_PASSWORD: str = config("REDIS_DEV_PASSWORD")
    # REDIS_DB: int = config("REDIS_DEV_DB")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW")
    SQLALCHEMY_ECHO: bool = True


# Environment map
config_options = {
    "production": ProductionConfig(),
    "staging": StagingConfig(),
    "development": DevelopmentConfig(),
}

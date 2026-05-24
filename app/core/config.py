from decouple import config
from pydantic import BaseModel, EmailStr

# Redis keys / streams
MOBILE_EVENTS_STREAM_KEY = "events:mobile:stream"
PAYMENT_PROGRESS_KEY_PREFIX = "payment:progress:"


class Config(BaseModel):
    # Common settings
    API_STR: str = config("API_STR", default="api/v1")
    PORT: int = config("PORT", 8000, cast=int)
    ACCESS_TOKEN_TTL: str = config("ACCESS_TOKEN_TTL", default="15m")
    REFRESH_TOKEN_TTL: str = config("REFRESH_TOKEN_TTL", default="30d")
    FASTAPI_ENV: str = config("FASTAPI_ENV", default="dev")

    SQLALCHEMY_DATABASE_URL: str

    MONGODB_DATABASE_URL: str = config("MONGODB_DATABASE_URL")
    MONGODB_DB_NAME: str = config("MONGODB_DB_NAME")

    BASE_URL: str = config("BASE_URL")
    REDIS_URL: str = config("REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = config("REDIS_MAX_CONNECTIONS", default=200, cast=int)
    REDIS_HEALTH_CHECK_INTERVAL: int = config(
        "REDIS_HEALTH_CHECK_INTERVAL", default=30, cast=int
    )
    SECRET_KEY: str = config("SECRET_KEY")
    PROJECT_NAME: str = config("PROJECT_NAME")

    # Chat uploads (Cloudinary presets configured outside the app)
    CHAT_IMAGES_PRESET: str = config("CHAT_IMAGES_PRESET", default="chat_images")
    CHAT_VIDEOS_PRESET: str = config("CHAT_VIDEOS_PRESET", default="chat_videos")
    CHAT_FILES_PRESET: str = config("CHAT_FILES_PRESET", default="chat_files")

    CHAT_IMAGES_MAX_BYTES: int = config(
        "CHAT_IMAGES_MAX_BYTES", default=10_485_760, cast=int
    )
    CHAT_VIDEOS_MAX_BYTES: int = config(
        "CHAT_VIDEOS_MAX_BYTES", default=26_214_400, cast=int
    )
    CHAT_FILES_MAX_BYTES: int = config(
        "CHAT_FILES_MAX_BYTES", default=10_485_760, cast=int
    )

    CHAT_IMAGES_ALLOWED_FORMATS: str = config(
        "CHAT_IMAGES_ALLOWED_FORMATS", default="jpg,jpeg,png,webp"
    )
    CHAT_VIDEOS_ALLOWED_FORMATS: str = config(
        "CHAT_VIDEOS_ALLOWED_FORMATS", default="mp4,webm"
    )
    CHAT_FILES_ALLOWED_FORMATS: str = config(
        "CHAT_FILES_ALLOWED_FORMATS", default="pdf,doc,docx,xls,xlsx,ppt,pptx"
    )

    # Optional self-ping job (used to keep some hosts from idling)
    SELF_PING_ENABLED: bool = config("SELF_PING_ENABLED", default=False, cast=bool)
    SELF_PING_URL: str | None = config("SELF_PING_URL", default=None)
    SELF_PING_ATTEMPTS: int = config("SELF_PING_ATTEMPTS", default=3, cast=int)
    SELF_PING_TIMEOUT_SECONDS: float = config(
        "SELF_PING_TIMEOUT_SECONDS", default=5.0, cast=float
    )
    SELF_PING_SLEEP_SECONDS: float = config(
        "SELF_PING_SLEEP_SECONDS", default=1.0, cast=float
    )

    RESERVATION_TTL: int = config("RESERVATION_TTL", default=300, cast=int)
    ALGORITHM: str = config("ALGORITHM")

    CLOUDINARY_KEY: str = config("CLOUDINARY_KEY")
    CLOUDINARY_SECRET: str = config("CLOUDINARY_SECRET")
    CLOUDINARY_NAME: str = config("CLOUDINARY_NAME")
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = config("EMAIL_VERIFICATION_EXPIRE_MINUTES")
    PROJECT_EMAIL: str = config("PROJECT_EMAIL")

    TRUST_X_FORWARDED_FOR: bool = config(
        "TRUST_X_FORWARDED_FOR", default=True, cast=bool
    )

    PAYSTACK_API_KEY: str = config("PAYSTACK_API_KEY")
    PAYSTACK_WEBHOOK_VERIFY_SIGNATURE: bool = config(
        "PAYSTACK_WEBHOOK_VERIFY_SIGNATURE", default=True, cast=bool
    )
    ALLOW_TEST_PAYSTACK_WEBHOOK: bool = config(
        "ALLOW_TEST_PAYSTACK_WEBHOOK", default=False, cast=bool
    )
    CELERY_ALWAYS_EAGER: bool = config("CELERY_ALWAYS_EAGER", default=False, cast=bool)

    # QSTASH
    QSTASH_API_KEY: str = config("QSTASH_API_KEY", default="")
    QSTASH_URL: str = config("QSTASH_URL", default="")
    QSTASH_TOKEN: str = config("QSTASH_TOKEN", default="")
    QSTASH_CURRENT_SIGNING_KEY: str = config("QSTASH_CURRENT_SIGNING_KEY", default="")
    QSTASH_NEXT_SIGNING_KEY: str = config("QSTASH_NEXT_SIGNING_KEY", default="")


class ProductionConfig(Config):
    NAME: str = "production"

    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_PROD_URL")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW")
    SQLALCHEMY_FUTURE: bool = config("SQLALCHEMY_FUTURE")
    SQLALCHEMY_ECHO: bool = False


class StagingConfig(Config):
    NAME: str = "staging"

    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_STAG_URL")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW")
    SQLALCHEMY_FUTURE: bool = True
    SQLALCHEMY_ECHO: bool = False

    # Using Staging
    RESEND_API_KEY: str = config("RESEND_API_KEY")
    RESEND_EMAIL: str = config("RESEND_EMAIL")


class DevelopmentConfig(Config):
    NAME: str = "dev"

    SQLALCHEMY_DATABASE_URL: str = config("SQLALCHEMY_DATABASE_DEV_URL")
    SQLALCHEMY_FUTURE: bool = config("SQLALCHEMY_FUTURE")
    SQLALCHEMY_POOL_SIZE: int = config("SQLALCHEMY_POOL_SIZE")
    SQLALCHEMY_MAX_OVERFLOW: int = config("SQLALCHEMY_MAX_OVERFLOW")
    SQLALCHEMY_ECHO: bool = False

    # Using SMTP
    SMTP_TLS: bool = config("SMTP_TLS", cast=bool)
    SMTP_SSL: bool = config("SMTP_SSL", cast=bool)
    SMTP_PORT: int = config("SMTP_PORT", cast=int)
    SMTP_HOST: str | None = config("SMTP_HOST")
    SMTP_USER: str | None = config("SMTP_USER")
    SMTP_PASSWORD: str = config("SMTP_PASSWORD")
    EMAILS_FROM_EMAIL: EmailStr = config("EMAILS_FROM_EMAIL")
    EMAILS_FROM_NAME: str = config("EMAILS_FROM_NAME")


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

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Redis keys / streams
MOBILE_EVENTS_STREAM_KEY = "events:mobile:stream"
PAYMENT_PROGRESS_KEY_PREFIX = "payment:progress:"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # =========================
    # Core config
    # =========================
    API_STR: str = "api/v1"
    PORT: int = 8000
    NAME: str = ""
    ACCESS_TOKEN_TTL: str = "15m"
    REFRESH_TOKEN_TTL: str = "30d"
    FASTAPI_ENV: str = "development"

    SQLALCHEMY_DATABASE_URL: str = ""
    SQLALCHEMY_DATABASE_DEV_URL: str = ""
    SQLALCHEMY_DATABASE_STAG_URL: str = ""
    SQLALCHEMY_DATABASE_PROD_URL: str = ""
    SQLALCHEMY_POOL_SIZE: int = 10
    SQLALCHEMY_MAX_OVERFLOW: int = 20
    SQLALCHEMY_FUTURE: bool = True
    SQLALCHEMY_ECHO: bool = False

    MONGODB_DATABASE_URL: str = ""
    MONGODB_DB_NAME: str = ""

    BASE_URL: str = ""
    REDIS_URL: str = ""
    REDIS_MAX_CONNECTIONS: int = 200
    REDIS_HEALTH_CHECK_INTERVAL: int = 30

    SECRET_KEY: str = ""
    PROJECT_NAME: str = ""

    # =========================
    # Cloudinary / uploads
    # =========================
    CHAT_IMAGES_PRESET: str = "chat_images"
    CHAT_VIDEOS_PRESET: str = "chat_videos"
    CHAT_FILES_PRESET: str = "chat_files"

    CHAT_IMAGES_MAX_BYTES: int = 10_485_760
    CHAT_VIDEOS_MAX_BYTES: int = 26_214_400
    CHAT_FILES_MAX_BYTES: int = 10_485_760

    CHAT_IMAGES_ALLOWED_FORMATS: str = "jpg,jpeg,png,webp"
    CHAT_VIDEOS_ALLOWED_FORMATS: str = "mp4,webm"
    CHAT_FILES_ALLOWED_FORMATS: str = "pdf,doc,docx,xls,xlsx,ppt,pptx"

    # =========================
    # System email
    # =========================
    BOUWNCE_SYSTEM_EMAIL: str = "support@bouwnce.com"
    BOUWNCE_SYSTEM_USERNAME: str = "bouwnce"
    BOUWNCE_SYSTEM_FULL_NAME: str = "Bouwnce"
    BOUWNCE_WELCOME_MESSAGE: str = "Welcome to Bouwnce! This is the official inbox."

    # =========================
    # Self ping
    # =========================
    SELF_PING_ENABLED: bool = False
    SELF_PING_URL: str | None = None
    SELF_PING_ATTEMPTS: int = 3
    SELF_PING_TIMEOUT_SECONDS: float = 5.0
    SELF_PING_SLEEP_SECONDS: float = 1.0

    RESERVATION_TTL: int = 300
    ALGORITHM: str = ""

    # =========================
    # Cloud / email / payments
    # =========================
    CLOUDINARY_KEY: str = ""
    CLOUDINARY_SECRET: str = ""
    CLOUDINARY_NAME: str = ""

    RESEND_API_KEY: str = ""
    RESEND_EMAIL: str = ""

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 465
    SMTP_HOST: str = ""
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = ""
    EMAILS_FROM_NAME: str = ""
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 30
    PROJECT_EMAIL: str = ""
    MAIL_TRAP_CODE: str = ""

    TRUST_X_FORWARDED_FOR: bool = True

    PAYSTACK_API_KEY: str = ""
    PAYSTACK_WEBHOOK_VERIFY_SIGNATURE: bool = True
    ALLOW_TEST_PAYSTACK_WEBHOOK: bool = False

    CELERY_ALWAYS_EAGER: bool = False

    # =========================
    # Newsletter
    # =========================
    NEWSLETTER_USE_TEST_RECIPIENTS: bool = False
    NEWSLETTER_TEST_RECIPIENTS: str = ""

    # =========================
    # Search matching
    # =========================
    SEARCH_MATCH_REGEX_SCORE: float = 0.99
    SEARCH_MATCH_NORMALIZED_SCORE: float = 0.98
    SEARCH_MATCH_PREFIX_SCORE: float = 0.97
    SEARCH_MATCH_TOKEN_CONTAINS_SCORE: float = 0.95
    SEARCH_MATCH_FUZZY_SCORE: float = 0.86
    SEARCH_MATCH_USER_SCORE: float = 0.92

    # =========================
    # QStash
    # =========================
    QSTASH_API_KEY: str = ""
    QSTASH_URL: str = ""
    QSTASH_TOKEN: str = ""
    QSTASH_CURRENT_SIGNING_KEY: str = ""
    QSTASH_NEXT_SIGNING_KEY: str = ""

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        if self.SQLALCHEMY_DATABASE_URL.strip():
            return self

        env_name = (self.FASTAPI_ENV or "").strip().lower()
        if env_name == "production":
            self.SQLALCHEMY_DATABASE_URL = self.SQLALCHEMY_DATABASE_PROD_URL
        elif env_name == "staging":
            self.SQLALCHEMY_DATABASE_URL = self.SQLALCHEMY_DATABASE_STAG_URL
        else:
            self.SQLALCHEMY_DATABASE_URL = self.SQLALCHEMY_DATABASE_DEV_URL

        return self


settings = Settings()

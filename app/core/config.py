import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Redis keys / streams
MOBILE_EVENTS_STREAM_KEY = "events:mobile:stream"
CHAT_EVENTS_STREAM_KEY_PREFIX = "chat:events:stream:"
CHAT_EVENTS_LAST_ID_KEY_PREFIX = "chat:events:last:"
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

    FRONTEND_URL: str = ""

    SQLALCHEMY_DATABASE_URL: str = ""
    SQLALCHEMY_DATABASE_DEV_URL: str = ""
    SQLALCHEMY_DATABASE_STAG_URL: str = ""
    SQLALCHEMY_DATABASE_PROD_URL: str = ""
    SQLALCHEMY_POOL_SIZE: int = 30
    SQLALCHEMY_MAX_OVERFLOW: int = 40
    SQLALCHEMY_FUTURE: bool = True
    SQLALCHEMY_ECHO: bool = False

    MONGODB_DATABASE_URL: str = ""
    MONGODB_DB_NAME: str = ""

    BASE_URL: str = ""
    REDIS_URL: str = ""
    # Upstash Free plan allows ~10 concurrent connections total.
    # Budget: API ~3, Celery worker ~3, Celery beat ~1, WebSocket ~3.
    # Each WebSocket user holds 1-2 connections (pubsub + xread).
    REDIS_MAX_CONNECTIONS: int = 50
    # Separate cap for long-blocking reads (XREAD BLOCK on /events/mobile).
    # Kept small so long-poll bursts can never drain the shared pool.
    REDIS_BLOCKING_MAX_CONNECTIONS: int = 20
    # Max concurrent connections the provider allows for this process's pools
    # (0 = unknown / not enforced). When set, the two pools above are shrunk so
    # their sum never exceeds it. Upstash Free is ~10.
    REDIS_CONNECTION_LIMIT: int = 0
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
    # Post-payment landing page Paystack redirects the payer to (optional:
    # falls back to the in-page review flow when unset).
    PAYSTACK_REDIRECT_URL: str = ""

    MAX_EVENT_TICKETS_PER_CLAIM: int = 10
    # Cloudinary folder for generated event-ticket QR images.
    EVENT_TICKET_QR_FOLDER: str = "event_tickets"

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
    # Search parser (LLM)
    # =========================
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    SEARCH_PARSER_LLM_ENABLED: bool = True
    SEARCH_PARSER_LLM_MODEL: str = ""
    SEARCH_PARSER_LLM_TIMEOUT: float = 10.0
    SEARCH_CACHE_CATALOG_TTL: int = 300
    SEARCH_CACHE_PARSE_TTL: int = 600

    # =========================
    # QStash
    # =========================
    QSTASH_API_KEY: str = ""
    QSTASH_URL: str = ""
    QSTASH_TOKEN: str = ""
    QSTASH_CURRENT_SIGNING_KEY: str = ""
    QSTASH_NEXT_SIGNING_KEY: str = ""

    # =========================
    # Web Push (VAPID)
    # =========================
    # Generate keys with: python -m pywebpush generate-vapid-keys
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    # mailto: contact (or https URL) shown to push service operators
    VAPID_SUBJECT: str = ""

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

    @model_validator(mode="after")
    def _enforce_redis_connection_budget(self) -> "Settings":
        """Clamp the two Redis pools so they fit the provider's connection cap.

        ``REDIS_MAX_CONNECTIONS`` + ``REDIS_BLOCKING_MAX_CONNECTIONS`` is the
        worst-case number of sockets this process opens.  On a provider with a
        hard per-account limit (e.g. Upstash Free ~10) an over-sized default
        would exhaust the provider rather than the pool.  When
        ``REDIS_CONNECTION_LIMIT`` is set we shrink the blocking pool first —
        its reads already degrade to non-blocking — and give the shared pool the
        remainder, while keeping at least one connection for each.
        """
        limit = int(getattr(self, "REDIS_CONNECTION_LIMIT", 0) or 0)
        if limit <= 0:
            return self

        main = max(int(self.REDIS_MAX_CONNECTIONS), 1)
        blocking = max(int(self.REDIS_BLOCKING_MAX_CONNECTIONS), 1)
        if main + blocking <= limit:
            return self

        if limit == 1:
            # No headroom to isolate: blocking reads share the single pooled
            # connection (get_blocking_redis_client() returns the main client).
            self.REDIS_MAX_CONNECTIONS = 1
            self.REDIS_BLOCKING_MAX_CONNECTIONS = 1
            warnings.warn(
                "REDIS_CONNECTION_LIMIT=1 cannot host separate shared and "
                "blocking pools; they will share a single connection.",
                stacklevel=2,
            )
            return self

        # Keep blocking to ~a quarter of the budget (never above its configured
        # value); the shared pool gets the rest.
        blocking = min(blocking, max(limit // 4, 1))
        self.REDIS_BLOCKING_MAX_CONNECTIONS = blocking
        self.REDIS_MAX_CONNECTIONS = max(limit - blocking, 1)
        return self


settings = Settings()

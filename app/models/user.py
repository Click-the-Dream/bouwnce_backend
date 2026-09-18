from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Self

from sqlalchemy import JSON, Boolean, DateTime, Enum, String, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, load_only, mapped_column, relationship

from app.core.security import genrate_verification_code
from app.models import BaseModel
from app.models.wallet import UserWallet
from app.utils.user_cache import (
    get_cached_user,
    set_cached_user,
)


@dataclass
class ChatUser:
    """Lightweight user object for chat — no SQLAlchemy state.

    Used for Redis-cached user data. Has the same attributes that the
    chat system reads from User (id, email, username, full_name, profile_pic)
    but without the ORM overhead.
    """

    id: str = ""
    email: str = ""
    username: str | None = None
    full_name: str | None = None
    profile_pic: dict | None = None


if TYPE_CHECKING:
    from app.event_broadcast.models.events import OutingEvent
    from app.matching_ground.model.interest import Interest
    from app.matching_ground.model.user_geolocation import UserGeolocation
    from app.matching_ground.model.user_interest import UserInterest
    from app.models import (
        Cart,
        Order,
        Payment,
        RefreshToken,
        Store,
        Verification,
    )


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String, nullable=True)
    institution: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_pic: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    profile_banner: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(
        Enum("user", "vendor", "admin", name="user_role_enum"), default="user"
    )
    gender: Mapped[str | None] = mapped_column(
        Enum("male", "female", "other", name="user_gender_enum"), nullable=True
    )
    otp: Mapped[str | None] = mapped_column(String(6))
    otp_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_store_owner: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )

    stores: Mapped[list[Store]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    verification: Mapped[Verification] = relationship(
        back_populates="user", uselist=False, lazy="joined"
    )

    carts: Mapped[list[Cart]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    payments: Mapped[list[Payment]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    orders: Mapped[list[Order]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="[Order.user_id]",
        lazy="selectin",
    )

    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    user_wallet: Mapped[UserWallet] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )

    user_interest: Mapped[list[UserInterest]] = relationship(back_populates="user")
    interests: Mapped[list[Interest]] = relationship(
        secondary="user_interests",
        back_populates="users",
        viewonly=True,
    )
    geolocation: Mapped[UserGeolocation] = relationship(back_populates="user")

    outing_events: Mapped[list[OutingEvent]] = relationship(
        back_populates="creator",
        cascade="all, delete-orphan",
        foreign_keys="[OutingEvent.creator_id]",
        lazy="selectin",
    )

    def to_dict(self):
        data_dict = super().to_dict()

        return data_dict

    @classmethod
    async def get_chat_users_by_ids(
        cls, ids: list[str], db: AsyncSession
    ) -> list[User]:
        """Fetch users for chat — Redis cache first, DB fallback.

        User chat data (id, email, username, full_name, profile_pic) changes
        rarely. Caching in Redis eliminates the DB round-trip on the hot path.
        """
        if not ids:
            return []

        unique_ids = list(set(str(uid) for uid in ids))
        users: list[User] = []
        uncached_ids: list[str] = []

        # 1. Check Redis cache
        for uid in unique_ids:
            cached = await get_cached_user(uid)
            if cached is not None:
                users.append(ChatUser(**cached))
            else:
                uncached_ids.append(uid)

        # 2. Fetch uncached users from DB
        if uncached_ids:
            stmt = (
                select(cls)
                .where(cls.id.in_(uncached_ids))
                .options(
                    load_only(
                        cls.id,
                        cls.email,
                        cls.username,
                        cls.full_name,
                        cls.profile_pic,
                    )
                )
            )
            result = await db.execute(stmt)
            db_users = list(result.scalars().all())

            # 3. Populate cache for DB results
            for u in db_users:
                users.append(u)
                await set_cached_user(
                    str(u.id),
                    {
                        "id": str(u.id),
                        "email": u.email or "",
                        "username": u.username,
                        "full_name": u.full_name,
                        "profile_pic": u.profile_pic,
                    },
                )

        return users

    @classmethod
    async def get_by_email(cls, email: str, db: AsyncSession) -> Self | None:

        result = await db.execute(select(cls).where(cls.email == email))

        return result.scalar_one_or_none()

    @classmethod
    async def get_by_username(cls, username: str, db: AsyncSession) -> Self | None:

        result = await db.execute(select(cls).where(cls.username == username))

        return result.scalar_one_or_none()

    @classmethod
    async def get_by_unique(
        cls,
        *,
        db: AsyncSession,
        email: str | None = None,
        username: str | None = None,
    ) -> Self | None:

        if email and username:
            query = select(cls).where(or_(cls.email == email, cls.username == username))
        elif email:
            query = select(cls).where(cls.email == email)
        elif username:
            query = select(cls).where(cls.username == username)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def generate_otp(self, db: AsyncSession) -> str:

        otp = genrate_verification_code()

        self.otp = otp
        self.otp_time = datetime.now(UTC) + timedelta(minutes=30)

        await db.flush()
        await db.refresh(self)

        return otp

    async def clear_otp(self, db: AsyncSession):

        self.otp = None
        self.otp_time = None

        await self.save(db)

    async def delete_me(self, db: AsyncSession) -> Self:

        self.is_deleted = True
        self.deleted_at = datetime.now(UTC)

        await self.save(db)

        return self

    async def update_me(self, user_data: dict, db: AsyncSession) -> Self:

        exclude = ["id", "created_at", "role"]
        for key, value in user_data.items():
            if hasattr(self, key) and key not in exclude:
                setattr(self, key, value)

        await self.save(db)
        return self

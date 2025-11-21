from datetime import UTC, datetime, timedelta
from typing import Self

from sqlalchemy import Boolean, Column, DateTime, Enum, String, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.core.security import genrate_verification_code
from app.models import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(
        Enum("user", "vendor", "admin", name="user_role_enum"), default="user"
    )
    otp = Column(String(6))
    otp_time = Column(DateTime(timezone=True))
    is_store_owner = Column(Boolean, server_default=text("false"), nullable=False)
    stores = relationship("Store", back_populates="user", cascade="all, delete-orphan")

    verification = relationship(
        "Verification",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    carts = relationship("Cart", back_populates="user", cascade="all, delete-orphan")

    payments = relationship(
        "Payment", back_populates="user", cascade="all, delete-orphan"
    )

    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan", foreign_keys="[Order.user_id]")

    def to_dict(self):
        data_dict = super().to_dict()

        return data_dict

    @classmethod
    async def get_by_email(cls, email: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.email == email))

        return result.scalar_one_or_none()

    @classmethod
    async def get_by_username(cls, username: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.username == username))

        return result.scalar_one_or_none()

    @classmethod
    async def get_by_unique(
        cls,
        *,
        db: AsyncSession,
        email: str | None = None,
        username: str | None = None,
    ) -> Self:

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

    async def clear_otp(self, db: AsyncSession) -> Self:

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

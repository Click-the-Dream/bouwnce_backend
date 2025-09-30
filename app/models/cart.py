from typing import Self

from sqlalchemy import Column, ForeignKey, Integer, String, delete
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.basemodel import BaseModel


class Cart(BaseModel):
    __tablename__ = "carts"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)

    @classmethod
    async def get_by_user_id(
        cls,
        user_id: str,
        db: AsyncSession,
        page: int | None = 1,
        page_size: int | None = 10,
    ) -> list[Self]:
        return await cls.get_by(
            {"user_id": user_id}, db, page=page, page_size=page_size
        )

    @classmethod
    async def delete_by_user_id(cls, user_id: str, db: AsyncSession):
        stm = delete(cls).where(cls.user_id == user_id)
        await db.execute(stm)

        return True

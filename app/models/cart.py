from typing import Self

from sqlalchemy import Column, ForeignKey, Integer, String, delete, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel
from app.utils.helper import is_valid_uuid


class Cart(BaseModel):
    __tablename__ = "carts"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)

    user = relationship("User", back_populates="carts", uselist=False)

    @classmethod
    async def get_by_user_id(
        cls,
        user_id: str,
        db: AsyncSession,
        page: int | None = 1,
        page_size: int | None = 10,
        all: bool = False,
    ) -> list[Self]:

        if not is_valid_uuid(user_id):
            raise TypeError("Invalid user Id")

        return await cls.get_by(
            filter={"user_id": user_id}, db=db, page=page, page_size=page_size, all=all
        )

    @classmethod
    async def delete_by_user_id(cls, user_id: str, db: AsyncSession):
        stm = delete(cls).where(cls.user_id == user_id)
        await db.execute(stm)

        return True

    @classmethod
    async def get_product_in_user_cart(
        cls, user_id: str, product_id: str, db: AsyncSession
    ):
        stm = select(cls).where(cls.user_id == user_id, cls.product_id == product_id)
        result = await db.execute(stm)

        return result.scalar_one_or_none()

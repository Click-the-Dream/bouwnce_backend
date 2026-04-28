from __future__ import annotations
from sqlalchemy.orm import relationship, Mapped, mapped_column, selectinload
from sqlalchemy import ForeignKey, Index, select, UniqueConstraint, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from typing import TYPE_CHECKING
from uuid  import UUID as UUID_PK

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.matching_ground.model.interest import Interest


class UserInterest(BaseModel):
    __tablename__ = "user_interests"
    
    user_id: Mapped[UUID_PK] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    interest_id: Mapped[UUID_PK] = mapped_column(ForeignKey("interests.id"), primary_key=True)
    
    user: Mapped["User"] = relationship(back_populates="user_interest")
    interest: Mapped["Interest"] = relationship(back_populates="user_interest")
    
    __table_args__ = (
        UniqueConstraint("user_id", "interest_id"),
        Index(
            "idx_user_interest",
            "user_id",
            "interest_id"
        )
    )
    
    
    @classmethod
    async def get_user_interests(cls, db: AsyncSession, user_id: str) -> list["Interest"]:
        query = (
            select(cls)
            .where(cls.user_id == user_id)
            .options(selectinload(cls.interest))
        )
        result= await db.execute(query)
        return [row.interest for row in result.scalars().all()]
    
    
    @classmethod
    async def add_user_interest(cls, db: AsyncSession, user_id: str, interest_ids: list[str]) -> bool:
        
        data = [
            {"user_id": user_id, "interest_id": interest_id} 
            for interest_id in interest_ids
        ]
        
        query = (
            insert(cls)
            .values(data)
            .on_conflict_do_nothing(index_elements=["user_id", "interest_id"])
        )
        
        await db.execute(query)
        return True
    
    @classmethod
    async def remove_user_interests(
        cls,
        db: AsyncSession,
        user_id: str,
        interest_ids: list[str]
    ) -> bool:
        
        query = (
            delete(cls)
            .where(
                cls.user_id == user_id,
                cls.insterest_id.in_(interest_ids)
            )
        )
        
        await db.execute(query)
        return True
    
    
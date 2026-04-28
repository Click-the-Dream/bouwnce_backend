from __future__ import annotations

from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession  
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import insert
from typing import TYPE_CHECKING, Self

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.matching_ground.model.user_interest import UserInterest
    from app.models.user import User



class Interest(BaseModel):
    __tablename__ = "interests"
    
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String, nullable=False)
    
    
    user_interest : Mapped[list["UserInterest"]] = relationship(back_populates="interest")
    
    users: Mapped["User"] = relationship(
        back_populates="interests",
        secondary="user_interests",
        viewonly=True
    )
    
    @classmethod
    async def create_interests(cls, db: AsyncSession, interest_list: dict[str, list[str]]) -> bool:
        data = []
        for category, interests in interest_list.items():
            for interest in interests:
                data.append({"name": interest, "category": category})
        
        query = (
            insert(cls)
            .values(data)
            .on_conflict_do_nothing(index_elements=["name"])
        )
        
        await db.execute(query)
        return True
        
    @classmethod
    async def get_all(cls, db: AsyncSession) -> list[Self]:
        result = await db.execute(select(cls).order_by(cls.category))
        
        return list(result.scalars().all())
    

    
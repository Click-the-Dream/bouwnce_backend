from datetime import UTC, datetime
from typing import Self
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, func, or_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgres_db_conn import Base


class BaseModel(Base):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:

        obj_dict = self.__dict__.copy()
        del obj_dict["_sa_instance_state"]
        del obj_dict["is_deleted"]
        del obj_dict["deleted_at"]
        obj_dict["id"] = str(self.id)
        if self.created_at:
            obj_dict["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            obj_dict["updated_at"] = self.updated_at.isoformat()
        if self.deleted_at:
            obj_dict["deleted_at"] = self.deleted_at.isoformat()

        return obj_dict

    async def save(self, db: AsyncSession) -> Self:

        self.updated_at = datetime.now(UTC)

        db.add(self)
        await db.flush()
        await db.refresh(self)

        return self

    @classmethod
    async def get_by_id(cls, id: str, db: AsyncSession) -> Self:
        result = await db.execute(select(cls).where(cls.id == id))

        obj = result.scalar_one_or_none()
        if not obj:
            raise ValueError(f"{cls.__name__} with the specified ID not found")
        return obj

    @classmethod
    async def delete_by_id(cls, id: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.id == id))
        obj = result.scalar_one_or_none()

        if not obj:
            raise ValueError(f"{cls.__name__} not found")

        obj.is_deleted = False
        obj.deleted_at = datetime.now(UTC)

        await obj.save(db)

        return obj

    @classmethod
    async def delete_permanently_by_id(cls, id: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.id == id))
        obj = result.scalar_one_or_none()

        if not obj:
            raise ValueError(f"{cls.__name__} not found")

        await db.delete(obj)

        await obj.save(db)

        return obj

    @classmethod
    async def create(cls, data: dict, db) -> Self:
        new_cls = cls(**data)
        db.add(new_cls)

        await db.flush()
        await db.refresh(new_cls)
        return new_cls

    @classmethod
    async def update_by_id(cls, id: str, data: dict, db: AsyncSession) -> Self:
        obj = await cls.get_by_id(id, db)
        if not obj:
            raise ValueError(f"{cls.__name__} not found")

        exclude = ["id", "created_at"]
        for key, value in data.items():
            if hasattr(obj, key) and key not in exclude:
                setattr(obj, key, value)

        await db.flush()
        await db.refresh(obj)

        return obj

    @classmethod
    async def get_by(
        cls, filter: dict, db: AsyncSession, page: int = 1, page_size: int = 10
    ) -> list[Self]:

        query = select(cls)
        or_condition = []

        for key, value in filter.items():
            if hasattr(cls, key):
                column = getattr(cls, key)
                if isinstance(value, str) and "%" in value:
                    or_condition.append(column.ilike(value))
                elif value is None:
                    or_condition.append(column.is_(None))
                else:
                    or_condition.append(column == value)

        if or_condition:
            query = query.where(or_(*or_condition))

        offset = (page - 1) * page_size

        count_query = query.with_only_columns(func.count()).order_by(None)
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        count_result = await db.execute(count_query)

        objs = result.scalars().all()
        count = count_result.scalar()

        return {"data": objs, "total": count, "page": page, "page_size": page_size}

    @classmethod
    async def undelete_by_id(cls, id: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.id == id))
        obj = result.scalar_one_or_none()

        if not obj:
            raise ValueError(f"{cls.__name__} not found")

        obj.is_deleted = False
        obj.deleted_at = None

        await obj.save(db)
        return obj

    async def delete(self, db: AsyncSession):
        await db.delete(self)
        await db.flush()

        return True

    @classmethod
    async def whoami(cls, id: str, user_type: str, db: AsyncSession):
        result = await db.execute(select(cls).where(cls.id == id))
        obj = result.scalar_one_or_none()

        if obj and obj.user_type == user_type:
            return obj
        return None 
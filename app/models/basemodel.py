from datetime import UTC, datetime
from typing import Any, Self, TypeVar
from uuid import UUID as UUID_Type
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, and_, func, or_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text

from app.db.postgres_db_conn import Base
from app.utils.helper import is_valid_uuid

T = TypeVar("T", bound="BaseModel")


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

        for key, value in obj_dict.items():
            if isinstance(value, (UUID_Type,)):
                obj_dict[key] = str(value)

            if isinstance(value, datetime):
                obj_dict[key] = value.isoformat()

        return obj_dict

    async def save(
        self, db: AsyncSession, attribute_names: list[str] | None = None
    ) -> Self:

        self.updated_at = datetime.now(UTC)

        db.add(self)
        await db.flush()
        if attribute_names:
            await db.refresh(self, attribute_names=attribute_names)
        else:
            await db.refresh(self)

        return self

    @classmethod
    async def get_by_id(cls, id: str, db: AsyncSession) -> Self:
        if not is_valid_uuid(id):
            raise TypeError("id not a valid uuid")

        if hasattr(cls, "is_active"):
            result = await db.execute(
                select(cls).where(and_(cls.is_active.is_(True), cls.id == id))
            )
        else:
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

        await db.commit()

        return obj

    @classmethod
    async def create(cls, data: dict, db: AsyncSession) -> Self:
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
        cls,
        db: AsyncSession,
        filter: dict | None = None,
        page: int = 1,
        page_size: int = 10,
        order_by: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:

        query = select(cls)
        or_condition = []

        if filter:
            for key, value in filter.items():
                if hasattr(cls, key):
                    column = getattr(cls, key)
                    if isinstance(value, str) and "%" in value:
                        or_condition.append(column.ilike(value))
                    elif value is None:
                        or_condition.append(column.is_(None))
                    else:
                        or_condition.append(column == value)

        if or_condition and hasattr(cls, "is_active"):
            query = query.filter(and_(cls.is_active.is_(True), or_(*or_condition)))
        elif or_condition:
            query = query.where(or_(*or_condition))

        if hasattr(cls, "created_at"):
            if date_from:
                query = query.where(cls.created_at >= text(f"'{date_from}'"))
            if date_to:
                query = query.where(cls.created_at <= text(f"'{date_to}'"))

        if order_by:
            descending = order_by.startswith("-")
            order_field = order_by.lstrip("-")
            if hasattr(cls, order_field):
                col = getattr(cls, order_field)
                query = query.order_by(col.desc() if descending else col.asc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        count_query = query.with_only_columns(func.count()).order_by(None)
        count_result = await db.execute(count_query)

        result = await db.execute(query)
        objs = result.scalars().all()
        count = count_result.scalar() or 0

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
        query = select(cls).where(cls.id == id, cls.role == user_type)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if user and user.role == user_type:
            return user
        return None

    @classmethod
    async def filter_by(
        cls: type[T],
        filter: dict[str, Any],
        db: AsyncSession,
        preload: list[str] | bool | None = None,
    ) -> list[T]:
        if preload is None:
            preload = []

        # if preload=True, load all relationships
        if preload is True:
            preload = [relation.key for relation in cls.__mapper__.relationships]

        query = select(cls)

        for relation in preload:
            if hasattr(cls, relation):
                query = query.options(selectinload(getattr(cls, relation)))

        for key, value in filter.items():
            if hasattr(cls, key):
                column = getattr(cls, key)
                if isinstance(value, str) and "%" in value:
                    query = query.where(column.ilike(value))
                elif value is None:
                    query = query.where(column.is_(None))
                else:
                    query = query.where(column == value)

        result = await db.execute(query)
        return result.scalars().all()

    async def update(self, db: AsyncSession, data: dict[str, Any]) -> Self:

        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

        db.add(self)
        await db.commit()
        await db.refresh(self)
        return self

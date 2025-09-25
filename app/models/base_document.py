from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Insert, Replace, before_event
from pydantic import Field


class BaseDocument(Document):
    created_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(UTC))]
    updated_at: Annotated[datetime, Field(default_factory=lambda: datetime.now(UTC))]

    @before_event([Replace, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(UTC)

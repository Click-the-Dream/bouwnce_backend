from __future__ import annotations

from typing import Any

from app.models.base_document import BaseDocument


class SearchParseCache(BaseDocument):

    message_hash: str
    domain: str
    raw_message: str
    fields: dict[str, Any]
    source: str

    class Settings:
        name = "search_parse_cache"
        indexes = [
            "message_hash",
            [("domain", 1), ("message_hash", 1)],
        ]


class SearchCatalogCache(BaseDocument):

    domain: str
    items: list[str]

    class Settings:
        name = "search_catalog_cache"
        indexes = [
            "domain",
        ]

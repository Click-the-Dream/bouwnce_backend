from __future__ import annotations

from abc import ABC, abstractmethod

from app.search_parser.schemas.schema import DomainConfig, ParsedQuery


class QueryParser(ABC):
    @abstractmethod
    async def parse(
        self,
        message: str,
        domain: DomainConfig,
        catalog: list[str] | None = None,
    ) -> ParsedQuery | None: ...

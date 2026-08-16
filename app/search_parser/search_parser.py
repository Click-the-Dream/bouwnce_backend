from __future__ import annotations

import hashlib
import json
import uuid

from app.core.config import settings
from app.search_parser.llm.openai_parser import OpenAIQueryParser
from app.search_parser.rule_based.fallback_parser import BuddySearchFallbackParser
from app.search_parser.schemas.parser import QueryParser
from app.search_parser.schemas.schema import (
    DomainConfig,
    ParsedQuery,
    get_domain_config,
)
from app.utils.exception import InternalServerErrorException


def _message_hash(message: str, domain_name: str) -> str:
    return hashlib.md5(
        f"{domain_name}:{message.strip().lower()}".encode(), usedforsecurity=False
    ).hexdigest()


async def _get_redis():
    from app.db.redis import get_redis_client

    return await get_redis_client()


async def _redis_get(key: str) -> str | None:
    try:
        redis = await _get_redis()
        return await redis.get(key)
    except Exception as err:
        raise InternalServerErrorException("Redis GET failed for") from err


async def _redis_set(key: str, value: str, ttl: int) -> None:
    try:
        redis = await _get_redis()
        await redis.set(key, value, ex=ttl)
    except Exception as err:
        raise InternalServerErrorException("Redis SET failed for") from err


def _catalog_key(domain_name: str) -> str:
    return f"search:catalog:{domain_name}"


async def _get_cached_catalog(domain_name: str) -> list[str] | None:
    raw = await _redis_get(_catalog_key(domain_name))
    if raw:
        items = json.loads(raw)
        print("Catalog from redis for %s, %d items", domain_name, len(items))
        return items

    try:
        from app.search_parser.model.parse_cache import SearchCatalogCache

        doc = await SearchCatalogCache.find_one(
            SearchCatalogCache.domain == domain_name
        )
        if doc:
            print("Catalog from mongo for %s, %d items", domain_name, len(doc.items))
            await _redis_set(
                _catalog_key(domain_name),
                json.dumps(doc.items),
                settings.SEARCH_CACHE_CATALOG_TTL,
            )
            return doc.items
    except Exception as err:
        raise InternalServerErrorException("Mongo catalog read failed for") from err


async def _set_cached_catalog(domain_name: str, items: list[str]) -> None:
    await _redis_set(
        _catalog_key(domain_name),
        json.dumps(items),
        settings.SEARCH_CACHE_CATALOG_TTL,
    )

    try:
        from app.search_parser.model.parse_cache import SearchCatalogCache

        existing = await SearchCatalogCache.find_one(
            SearchCatalogCache.domain == domain_name
        )
        if existing:
            existing.items = items
            await existing.save()
        else:
            doc = SearchCatalogCache(domain=domain_name, items=items)
            await doc.insert()
    except Exception as err:
        raise InternalServerErrorException("Mongo catalog write failed for") from err


def _parse_redis_key(domain_name: str, msg_hash: str) -> str:
    return f"search:parse:{domain_name}:{msg_hash}"


async def _get_cached_parse(message: str, domain_name: str) -> ParsedQuery | None:
    msg_hash = _message_hash(message, domain_name)

    raw = await _redis_get(_parse_redis_key(domain_name, msg_hash))
    if raw:
        data = json.loads(raw)
        print("Parse from redis for %s: %s", domain_name, message[:50])
        return ParsedQuery(
            fields=data["fields"],
            raw_message=data["raw_message"],
            source=data["source"],
        )

    try:
        from app.search_parser.model.parse_cache import SearchParseCache

        doc = await SearchParseCache.find_one(
            SearchParseCache.domain == domain_name,
            SearchParseCache.message_hash == msg_hash,
        )
        if doc:
            print("Parse from mongo for %s: %s", domain_name, message[:50])
            parsed = ParsedQuery(
                fields=doc.fields,
                raw_message=doc.raw_message,
                source=doc.source,
            )
            await _set_cached_parse(message, domain_name, parsed)
            return parsed
    except Exception as err:
        raise InternalServerErrorException("Mongo parse read failed for") from err


async def _set_cached_parse(
    message: str, domain_name: str, parsed: ParsedQuery
) -> None:
    msg_hash = _message_hash(message, domain_name)

    data = {
        "fields": parsed.fields,
        "raw_message": parsed.raw_message,
        "source": parsed.source,
    }
    await _redis_set(
        _parse_redis_key(domain_name, msg_hash),
        json.dumps(data),
        settings.SEARCH_CACHE_PARSE_TTL,
    )

    try:
        from app.search_parser.model.parse_cache import SearchParseCache

        existing = await SearchParseCache.find_one(
            SearchParseCache.domain == domain_name,
            SearchParseCache.message_hash == msg_hash,
        )
        if existing:
            existing.fields = parsed.fields
            existing.raw_message = parsed.raw_message
            existing.source = parsed.source
            await existing.save()
        else:
            doc = SearchParseCache(
                message_hash=msg_hash,
                domain=domain_name,
                raw_message=parsed.raw_message,
                fields=parsed.fields,
                source=parsed.source,
            )
            await doc.insert()
    except Exception as err:
        raise InternalServerErrorException("Mongo parse write failed for") from err


class CompositeQueryParser(QueryParser):

    def __init__(
        self,
        *,
        llm_parser: OpenAIQueryParser | None = None,
        fallback_parser: BuddySearchFallbackParser | None = None,
    ) -> None:
        self._llm = llm_parser or OpenAIQueryParser()
        self._fallback = fallback_parser or BuddySearchFallbackParser()

    async def _fetch_catalog(
        self, session: object, domain: DomainConfig, domain_name: str
    ) -> list[str] | None:
        if not domain.include_catalog:
            return None

        cached = await _get_cached_catalog(domain_name)
        if cached is not None:
            return cached

        from sqlalchemy.ext.asyncio import AsyncSession

        db: AsyncSession = session
        catalog = (
            await domain.fetch_catalog(db) if hasattr(domain, "fetch_catalog") else None
        )

        if catalog:
            await _set_cached_catalog(domain_name, catalog)
            return catalog

        return None

    def _gate_llm_output(
        self,
        parsed: ParsedQuery,
        domain: DomainConfig,
        catalog: list[str] | None,
    ) -> ParsedQuery:

        catalog_field = domain.catalog_field
        llm_items = parsed.fields.get(catalog_field, [])
        if not llm_items or not catalog:
            return parsed

        from app.matching_ground.core.interest_normalization import (
            normalize_interest_name,
        )
        from app.search_parser.rule_based.fallback_parser import (
            BuddySearchFallbackParser,
        )

        known_norm = {normalize_interest_name(n): n for n in catalog}

        validated: list[str] = []
        for item in llm_items:
            norm = normalize_interest_name(item)

            if norm in known_norm:
                validated.append(known_norm[norm])
                continue

            best_score = 0.0
            best_match = None
            for cat_name in catalog:
                score = BuddySearchFallbackParser._score_text_match(item, cat_name)
                if score > best_score:
                    best_score = score
                    best_match = cat_name

            if best_score < settings.SEARCH_MATCH_FUZZY_SCORE:
                for cat_name in catalog:
                    score = BuddySearchFallbackParser._score_text_match(
                        parsed.raw_message, cat_name
                    )
                    if score > best_score:
                        best_score = score
                        best_match = cat_name

            if best_score >= settings.SEARCH_MATCH_FUZZY_SCORE and best_match:
                print(
                    "Mapped %s %r → %r (score=%.2f)",
                    domain.catalog_field,
                    item,
                    best_match,
                    best_score,
                )
                validated.append(best_match)
            else:
                print(
                    "Discarded %s %r (best=%.2f, threshold=%.2f)",
                    domain.catalog_field,
                    item,
                    best_score,
                    settings.SEARCH_MATCH_FUZZY_SCORE,
                )

        gated_fields = {**parsed.fields, catalog_field: validated}
        return ParsedQuery(
            fields=gated_fields,
            raw_message=parsed.raw_message,
            source=parsed.source,
        )

    def _llm_result_has_content(
        self, parsed: ParsedQuery, domain: DomainConfig
    ) -> bool:
        """Check if the LLM result has at least one meaningful field."""
        for field_name in domain.gate_fields:
            value = parsed.fields.get(field_name)
            if value:
                if isinstance(value, list) and len(value) > 0:
                    return True
                if not isinstance(value, list) and value is not None:
                    return True
        return False

    async def parse(
        self,
        message: str,
        domain: DomainConfig,
        catalog: list[str] | None = None,
    ) -> ParsedQuery | None:
        if not message.strip():
            return None

        if settings.SEARCH_PARSER_LLM_ENABLED:
            result = await self._llm.parse(message, domain, catalog)
            if result is not None:
                return result

        return await self._fallback.parse(message, domain, catalog)

    async def parse_with_session(
        self,
        session: object,
        message: str,
        domain_name: str,
        requester_id: uuid.UUID,
    ) -> ParsedQuery | None:
        if not message.strip():
            return None

        cached_parse = await _get_cached_parse(message, domain_name)
        if cached_parse is not None:
            if cached_parse.source != "llm" and settings.SEARCH_PARSER_LLM_ENABLED:
                print(
                    f"cached result is from {cached_parse.source!r}, retrying with LLM"
                )
            else:
                return cached_parse

        domain = get_domain_config(domain_name)
        catalog = await self._fetch_catalog(session, domain, domain_name)

        if settings.SEARCH_PARSER_LLM_ENABLED:
            print(f"trying LLM for domain={domain_name}")
            result = await self._llm.parse(message, domain, catalog)
            if result is not None:
                print("LLM succeeded, gating output")
                result = self._gate_llm_output(result, domain, catalog)
                if self._llm_result_has_content(result, domain):
                    print(
                        f"LLM gated result accepted — fields with data: "
                        f"{[f for f in domain.gate_fields if result.fields.get(f)]}"
                    )
                    await _set_cached_parse(message, domain_name, result)
                    return result
                print("LLM output gated to empty — falling back to rules")
        else:
            print("LLM disabled, using rule-based fallback")

        print(f"falling back to rule-based parser for domain={domain_name}")
        result = await self._fallback.parse_with_session(
            session, message, domain, requester_id
        )
        if result is not None:
            await _set_cached_parse(message, domain_name, result)
        return result

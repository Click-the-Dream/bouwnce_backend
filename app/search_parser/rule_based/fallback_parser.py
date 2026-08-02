from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.core.config import settings
from app.search_parser.schemas.parser import QueryParser
from app.search_parser.schemas.schema import BuddySearchQuery, DomainConfig, ParsedQuery


class BuddySearchFallbackParser(QueryParser):

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(
            token for token in re.split(r"[^a-z0-9]+", (value or "").lower()) if token
        )

    @staticmethod
    def _singularize_token(token: str) -> str:
        if len(token) <= 3:
            return token
        if token.endswith("ies") and len(token) > 4:
            return f"{token[:-3]}y"
        if token.endswith("es") and len(token) > 4:
            return token[:-2]
        if token.endswith("s") and not token.endswith("ss"):
            return token[:-1]
        return token

    @staticmethod
    def _score_text_match(left: str, right: str) -> float:
        left_norm = BuddySearchFallbackParser._normalize_text(left)
        right_norm = BuddySearchFallbackParser._normalize_text(right)
        if not left_norm or not right_norm:
            return 0.0
        if left_norm == right_norm:
            return 1.0

        regex_patterns = [
            rf"(?<![a-z0-9]){re.escape(right_norm)}(?![a-z0-9])",
            rf"(?<![a-z0-9]){re.escape(BuddySearchFallbackParser._singularize_token(right_norm))}(?![a-z0-9])",
        ]
        for pattern in regex_patterns:
            if re.search(pattern, left_norm):
                return settings.SEARCH_MATCH_REGEX_SCORE

        if right_norm in left_norm:
            return settings.SEARCH_MATCH_NORMALIZED_SCORE

        prompt_tokens = BuddySearchFallbackParser._normalize_text(left_norm).split()
        interest_tokens = BuddySearchFallbackParser._normalize_text(right_norm).split()
        if not prompt_tokens or not interest_tokens:
            return SequenceMatcher(None, left_norm, right_norm).ratio()

        best_score = 0.0
        for pt in prompt_tokens:
            pv = {pt, BuddySearchFallbackParser._singularize_token(pt)}
            for it in interest_tokens:
                iv = {it, BuddySearchFallbackParser._singularize_token(it)}
                for p in pv:
                    for i in iv:
                        if not p or not i:
                            continue
                        if p == i:
                            best_score = max(
                                best_score, settings.SEARCH_MATCH_PREFIX_SCORE
                            )
                        elif p in i or i in p:
                            best_score = max(
                                best_score, settings.SEARCH_MATCH_TOKEN_CONTAINS_SCORE
                            )
                        else:
                            best_score = max(
                                best_score, SequenceMatcher(None, p, i).ratio()
                            )

        if best_score >= settings.SEARCH_MATCH_FUZZY_SCORE:
            return best_score
        return SequenceMatcher(None, left_norm, right_norm).ratio()

    async def parse(
        self,
        message: str,
        domain: DomainConfig,
        catalog: list[str] | None = None,
    ) -> ParsedQuery | None:
        """Lightweight fallback — uses catalog-based matching (no DB session needed)."""
        if not message.strip():
            return None

        text = message.strip()

        radius_km = self._parse_radius_km(text)

        interest_names: list[str] = []
        if catalog and domain.output_model == BuddySearchQuery:
            interest_names = self._match_interests_from_catalog(text, catalog)

        return ParsedQuery(
            fields={
                "interests": interest_names,
                "radius_km": radius_km,
                "user_references": [],
                "intent_summary": text,
            },
            raw_message=message,
            source="fallback",
        )

    @staticmethod
    def _parse_radius_km(message: str) -> float | None:
        text = (message or "").strip()
        if not text:
            return None
        radius_match = re.search(
            r"(?i)(?:within|radius|around|near|in)\s*(\d+(?:\.\d+)?)\s*km", text
        )
        if radius_match:
            try:
                return float(radius_match.group(1))
            except ValueError:
                return None
        return None

    def _match_interests_from_catalog(
        self, message: str, catalog: list[str]
    ) -> list[str]:
        from app.matching_ground.core.interest_normalization import (
            normalize_interest_name,
        )

        exact_hits: list[str] = []
        normalized_hits: list[str] = []
        fuzzy_hits: list[tuple[float, str]] = []

        for name in catalog:
            score = self._score_text_match(message, name)
            norm_name = normalize_interest_name(name)
            if score >= settings.SEARCH_MATCH_REGEX_SCORE:
                exact_hits.append(norm_name)
            elif score >= settings.SEARCH_MATCH_NORMALIZED_SCORE:
                normalized_hits.append(norm_name)
            elif score >= settings.SEARCH_MATCH_FUZZY_SCORE:
                fuzzy_hits.append((score, norm_name))

        if exact_hits:
            hits = exact_hits
        elif normalized_hits:
            hits = normalized_hits
        else:
            fuzzy_hits.sort(key=lambda item: (-item[0], item[1].lower()))
            hits = [name for _, name in fuzzy_hits]

        seen: set[str] = set()
        result: list[str] = []
        for name in hits:
            if name in seen:
                continue
            seen.add(name)
            result.append(name)
            if len(result) >= 5:
                break
        return result

    async def parse_with_session(
        self,
        session: object,
        message: str,
        domain: DomainConfig,
        requester_id: object,
    ) -> ParsedQuery | None:
        if not message.strip():
            return None

        import uuid

        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.matching_ground.core.interest_normalization import (
            normalize_interest_name,
        )
        from app.matching_ground.service.matching.match_lifecycle import (
            MatchLifecycleService,
        )
        from app.models.user import User

        db: AsyncSession = session  # type: ignore[assignment]
        uid: uuid.UUID = requester_id  # type: ignore[assignment]
        text = message.strip()

        lifecycle = MatchLifecycleService()
        radius_km = lifecycle._parse_radius_km(text)
        interest_hints = await lifecycle._extract_interest_hints(db, text)
        interest_names = list(interest_hints) if interest_hints else []

        target_user_ids = await lifecycle._extract_user_hints(db, text)

        user_refs: list[str] = []
        if target_user_ids:
            rows = await db.execute(
                select(User.username, User.full_name).where(
                    User.id.in_(list(target_user_ids))
                )
            )
            for username, full_name in rows.all():
                name = full_name if full_name else username
                if name:
                    user_refs.append(name)

        return ParsedQuery(
            fields={
                "interests": interest_names,
                "radius_km": radius_km,
                "user_references": user_refs,
                "intent_summary": text,
            },
            raw_message=message,
            source="fallback",
        )

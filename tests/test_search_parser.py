from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.search_parser.schemas.schema import (
    BuddySearchQuery,
    DomainConfig,
    DOMAIN_REGISTRY,
    ParsedQuery,
    ProductSearchQuery,
    BUDDY_SEARCH_DOMAIN,
    PRODUCT_SEARCH_DOMAIN,
    get_domain_config,
)
from app.search_parser.llm.prompt_builder import (
    build_system_prompt,
    build_catalog_section,
    build_messages,
)
from app.search_parser.llm.openai_parser import OpenAIQueryParser
from app.search_parser.rule_based.fallback_parser import BuddySearchFallbackParser
from app.search_parser.search_parser import CompositeQueryParser


pytestmark = pytest.mark.asyncio(scope="module")


# ---------------------------------------------------------------------------
# Schema / Domain models
# ---------------------------------------------------------------------------


class TestBuddySearchQuery:
    def test_basic_creation(self):
        q = BuddySearchQuery(
            interests=["ai", "cycling"],
            radius_km=5.0,
            user_references=["john"],
            intent_summary="someone into AI near 5km",
        )
        assert q.interests == ["ai", "cycling"]
        assert q.radius_km == 5.0
        assert q.user_references == ["john"]

    def test_defaults(self):
        q = BuddySearchQuery(interests=["ai"], intent_summary="test")
        assert q.radius_km is None
        assert q.user_references == []

    def test_model_dump(self):
        q = BuddySearchQuery(interests=["ai"], radius_km=10.0, user_references=[], intent_summary="test")
        dump = q.model_dump()
        assert "interests" in dump
        assert dump["radius_km"] == 10.0


class TestProductSearchQuery:
    def test_basic_creation(self):
        q = ProductSearchQuery(
            categories=["electronics"], brands=["sony"],
            price_min=100.0, price_max=500.0,
            attributes=["wireless"], intent_summary="test",
        )
        assert q.categories == ["electronics"]
        assert q.price_max == 500.0

    def test_defaults(self):
        q = ProductSearchQuery(categories=["books"], intent_summary="test")
        assert q.brands == []
        assert q.price_min is None


class TestParsedQuery:
    def test_creation(self):
        pq = ParsedQuery(
            fields={"interests": ["ai"]}, raw_message="test", source="llm",
        )
        assert pq.source == "llm"
        assert pq.fields["interests"] == ["ai"]

    def test_fallback_source(self):
        pq = ParsedQuery(fields={"interests": ["cycling"]}, raw_message="test", source="fallback")
        assert pq.source == "fallback"


class TestDomainRegistry:
    def test_registry_keys(self):
        assert "buddy" in DOMAIN_REGISTRY
        assert "product" in DOMAIN_REGISTRY

    def test_get_domain_config_buddy(self):
        dc = get_domain_config("buddy")
        assert dc.output_model == BuddySearchQuery

    def test_get_domain_config_product(self):
        dc = get_domain_config("product")
        assert dc.output_model == ProductSearchQuery

    def test_get_domain_config_unknown(self):
        with pytest.raises(ValueError, match="Unknown search domain"):
            get_domain_config("nonexistent")


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_build_system_prompt_buddy(self):
        prompt = build_system_prompt(BUDDY_SEARCH_DOMAIN)
        assert "buddy" in prompt.lower() or "search" in prompt.lower()
        assert "Expected output fields" in prompt

    def test_build_catalog_section_small(self):
        section = build_catalog_section(["ai", "cycling"], BUDDY_SEARCH_DOMAIN)
        assert section is not None
        assert "ai" in section

    def test_build_catalog_section_empty(self):
        assert build_catalog_section(None, BUDDY_SEARCH_DOMAIN) is None

    def test_build_catalog_section_disabled(self):
        dc = DomainConfig(output_model=BuddySearchQuery, system_prompt_template="test", include_catalog=False)
        assert build_catalog_section(["ai"], dc) is None

    def test_build_catalog_section_too_large(self):
        dc = DomainConfig(output_model=BuddySearchQuery, system_prompt_template="test", include_catalog=True, catalog_max_size=5)
        assert build_catalog_section(["a", "b", "c", "d", "e", "f"], dc) is None

    def test_build_messages(self):
        msgs = build_messages("I want someone into AI", BUDDY_SEARCH_DOMAIN, ["ai"])
        assert len(msgs) == 2
        assert msgs[1]["content"] == "I want someone into AI"

    def test_build_messages_no_catalog(self):
        msgs = build_messages("hello", BUDDY_SEARCH_DOMAIN, None)
        assert "Known values" not in msgs[0]["content"]


# ---------------------------------------------------------------------------
# OpenAI parser (mocked)
# ---------------------------------------------------------------------------


class TestOpenAIQueryParser:
    async def test_parse_success(self):
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(
                content='{"interests": ["ai", "cycling"], "radius_km": 5.0, "user_references": [], "intent_summary": "test"}'
            ))
        ]
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        parser = OpenAIQueryParser()
        parser._client = mock_instance

        result = await parser.parse("someone into AI near 5km", BUDDY_SEARCH_DOMAIN, ["ai"])
        assert result is not None
        assert result.source == "llm"
        assert result.fields["interests"] == ["ai", "cycling"]

    async def test_parse_empty_message(self):
        parser = OpenAIQueryParser()
        result = await parser.parse("", BUDDY_SEARCH_DOMAIN)
        assert result is None

    async def test_parse_api_failure(self):
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(side_effect=Exception("API error"))

        parser = OpenAIQueryParser()
        parser._client = mock_instance
        result = await parser.parse("test", BUDDY_SEARCH_DOMAIN)
        assert result is None

    async def test_parse_invalid_json(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="not json"))]
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        parser = OpenAIQueryParser()
        parser._client = mock_instance
        result = await parser.parse("test", BUDDY_SEARCH_DOMAIN)
        assert result is None


# ---------------------------------------------------------------------------
# Fallback parser
# ---------------------------------------------------------------------------


class TestBuddySearchFallbackParser:
    async def test_parse_empty_message(self):
        parser = BuddySearchFallbackParser()
        result = await parser.parse("", BUDDY_SEARCH_DOMAIN)
        assert result is None

    async def test_parse_with_catalog(self):
        parser = BuddySearchFallbackParser()
        result = await parser.parse("someone into AI near 5km", BUDDY_SEARCH_DOMAIN, ["ai", "cycling", "coding"])
        assert result is not None
        assert result.source == "fallback"
        assert "ai" in result.fields["interests"]
        assert result.fields["radius_km"] == 5.0

    async def test_parse_no_interests(self):
        parser = BuddySearchFallbackParser()
        result = await parser.parse("random nonsense", BUDDY_SEARCH_DOMAIN)
        assert result is not None
        assert result.source == "fallback"
        assert result.fields["interests"] == []

    async def test_parse_radius_extraction(self):
        parser = BuddySearchFallbackParser()
        result = await parser.parse("within 10km", BUDDY_SEARCH_DOMAIN)
        assert result is not None
        assert result.fields["radius_km"] == 10.0

    async def test_parse_no_radius(self):
        parser = BuddySearchFallbackParser()
        result = await parser.parse("someone into cycling", BUDDY_SEARCH_DOMAIN, ["cycling"])
        assert result is not None
        assert result.fields["radius_km"] is None

    def test_score_text_match_exact(self):
        score = BuddySearchFallbackParser._score_text_match("ai", "ai")
        assert score == 1.0

    def test_score_text_match_fuzzy(self):
        score = BuddySearchFallbackParser._score_text_match("machine learning", "ai")
        assert score > 0.0

    def test_normalize_text(self):
        result = BuddySearchFallbackParser._normalize_text("  Machine   Learning  ")
        assert result == "machine learning"


# ---------------------------------------------------------------------------
# Composite parser (mocked)
# ---------------------------------------------------------------------------


class TestCompositeQueryParser:
    async def test_llm_first_success(self):
        mock_llm = AsyncMock(spec=OpenAIQueryParser)
        mock_llm.parse = AsyncMock(
            return_value=ParsedQuery(
                fields={"interests": ["ai"], "radius_km": 5.0, "user_references": [], "intent_summary": "test"},
                raw_message="test", source="llm",
            )
        )
        parser = CompositeQueryParser(llm_parser=mock_llm)
        result = await parser.parse("someone into AI", BUDDY_SEARCH_DOMAIN, ["ai"])
        assert result.source == "llm"
        mock_llm.parse.assert_called_once()

    async def test_llm_failure_fallback(self):
        mock_llm = AsyncMock(spec=OpenAIQueryParser)
        mock_llm.parse = AsyncMock(return_value=None)
        mock_fallback = AsyncMock(spec=BuddySearchFallbackParser)
        mock_fallback.parse = AsyncMock(
            return_value=ParsedQuery(
                fields={"interests": ["ai"], "radius_km": None, "user_references": [], "intent_summary": "test"},
                raw_message="test", source="fallback",
            )
        )
        parser = CompositeQueryParser(llm_parser=mock_llm, fallback_parser=mock_fallback)
        result = await parser.parse("test", BUDDY_SEARCH_DOMAIN)
        assert result.source == "fallback"

    async def test_llm_disabled_uses_fallback(self):
        mock_llm = AsyncMock(spec=OpenAIQueryParser)
        mock_fallback = AsyncMock(spec=BuddySearchFallbackParser)
        mock_fallback.parse = AsyncMock(
            return_value=ParsedQuery(
                fields={"interests": ["cycling"], "radius_km": None, "user_references": [], "intent_summary": "test"},
                raw_message="test", source="fallback",
            )
        )
        with patch("app.search_parser.search_parser.settings.SEARCH_PARSER_LLM_ENABLED", False):
            parser = CompositeQueryParser(llm_parser=mock_llm, fallback_parser=mock_fallback)
            result = await parser.parse("test", BUDDY_SEARCH_DOMAIN)
            assert result.source == "fallback"
            mock_llm.parse.assert_not_called()

    async def test_empty_message_returns_none(self):
        parser = CompositeQueryParser()
        result = await parser.parse("", BUDDY_SEARCH_DOMAIN)
        assert result is None

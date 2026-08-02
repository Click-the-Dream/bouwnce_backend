from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Core abstractions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedQuery:
    """Generic result from any query parser."""

    fields: dict[str, Any]
    raw_message: str
    source: str  # "llm" or "fallback"


@dataclass
class DomainConfig:
    """Wire-up between a domain's Pydantic output model and LLM prompting."""

    output_model: type[BaseModel]
    system_prompt_template: str
    examples: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    include_catalog: bool = True
    catalog_max_size: int = 200
    # Name of the list field in output_model that holds catalog-matched items
    catalog_field: str = "interests"
    # Fields that must have at least one entry for the LLM result to be accepted
    # (if all are empty, the result is discarded and fallback is used)
    gate_fields: list[str] = field(
        default_factory=lambda: ["interests", "user_references"]
    )
    # Async callable to fetch catalog items from the DB.
    # Signature: async (db: AsyncSession) -> list[str] | None
    fetch_catalog: Any = None


# ---------------------------------------------------------------------------
# Domain-specific output models
# ---------------------------------------------------------------------------


class BuddySearchQuery(BaseModel):
    """Structured output the LLM produces for buddy / interest search."""

    interests: list[str] = Field(
        description="Interest topics the user is looking for, drawn from the catalog if provided",
    )
    radius_km: float | None = Field(
        default=None,
        description="Distance radius in kilometers if the user mentions proximity",
    )
    user_references: list[str] = Field(
        default_factory=list,
        description="User names or handles explicitly mentioned in the message",
    )
    intent_summary: str = Field(
        description="Brief summary of what the user is looking for",
    )


class ProductSearchQuery(BaseModel):
    """Structured output for product / marketplace search."""

    categories: list[str] = Field(
        description="Product categories the user is looking for",
    )
    brands: list[str] = Field(
        default_factory=list,
        description="Specific brands mentioned",
    )
    price_min: float | None = Field(
        default=None,
        description="Minimum price if mentioned",
    )
    price_max: float | None = Field(
        default=None,
        description="Maximum price if mentioned",
    )
    attributes: list[str] = Field(
        default_factory=list,
        description="Additional attributes like color, size, material",
    )
    intent_summary: str = Field(
        description="Brief summary of what the user is looking for",
    )


# ---------------------------------------------------------------------------
# Buddy search domain config with rich prompt + few-shot examples
# ---------------------------------------------------------------------------

_BUDDY_SYSTEM_PROMPT = """\
You are a search query parser for a buddy-matching social platform called Bouwnce.
Your job is to convert the user's free-text search message into structured search
parameters that the backend can use to find matching people.

EXTRACTION RULES:

1. **Interests** — Extract every topic or activity the user mentions.
   - If a catalog of known interests is provided, you MUST map the user's words
     to the closest matching catalog entry. Use the catalog spelling EXACTLY.
     For example, if the user says "study" and the catalog has "Reading" or
     "Personal Development", pick the closest match from the catalog.
   - You MUST ONLY return interests that exist in the catalog. If the user's
     interest doesn't exactly match a catalog entry, pick the semantically
     closest one (e.g. "study" → "Reading", "working out" → "Gym/Fitness").
   - Apply synonym normalization:
     * "machine learning", "ML", "artificial intelligence" → "ai"
     * "programming", "software development", "coding" → "coding"
     * "bicycle", "bike", "biking", "road cycling" → "cycling"
   - NEVER return an interest that is not in the catalog. If no catalog entry
     is a reasonable match, return an empty interests list.

2. **Radius** — Extract radius_km only when the user states an explicit distance.
   - Recognize patterns: "within X km", "near Xkm", "around X km", "radius X km",
     "X km away", "less than X km".
   - If no distance is mentioned, return null — DO NOT guess a default.

3. **User references** — Extract names or handles the user explicitly names.
   - Only include names that clearly refer to a specific person (e.g. "find @john"
     or "someone named Sarah").
   - Do NOT extract generic references like "someone", "a person", "people".

4. **Intent summary** — Write a short (one sentence) summary of what the user wants.

5. **Empty / ambiguous messages** — If the message is vague or contains no
   extractable information, return empty lists and null radius. Never fabricate
   interests or distances that the user did not mention.

OUTPUT FORMAT:
Return valid JSON matching the schema. Every field must be present.
"""

_BUDDY_EXAMPLES: list[tuple[str, dict[str, Any]]] = [
    (
        "I want someone into machine learning within 5km",
        {
            "interests": ["ai"],
            "radius_km": 5.0,
            "user_references": [],
            "intent_summary": "User wants to find buddies interested in AI within a 5km radius.",
        },
    ),
    (
        "find me bikers near 10km",
        {
            "interests": ["cycling"],
            "radius_km": 10.0,
            "user_references": [],
            "intent_summary": "User wants to find cycling buddies within 10km.",
        },
    ),
    (
        "looking for @jane who likes coding",
        {
            "interests": ["coding"],
            "radius_km": None,
            "user_references": ["jane"],
            "intent_summary": "User wants to find a specific person named Jane who is into coding.",
        },
    ),
    (
        "someone near me into reading and podcast",
        {
            "interests": ["reading", "podcast"],
            "radius_km": None,
            "user_references": [],
            "intent_summary": "User wants to find buddies interested in reading and podcasts nearby.",
        },
    ),
    (
        "any cool people around",
        {
            "interests": [],
            "radius_km": None,
            "user_references": [],
            "intent_summary": "User wants to find any people nearby, with no specific interest filter.",
        },
    ),
]


async def _fetch_buddy_interests(db: object) -> list[str] | None:
    """Fetch interest names from PostgreSQL for the buddy domain."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.matching_ground.model.interest import Interest

    session: AsyncSession = db  # type: ignore[assignment]
    rows = await session.execute(select(Interest.name))
    names = sorted(r[0] for r in rows.all() if r and r[0])
    return names if names else None


BUDDY_SEARCH_DOMAIN = DomainConfig(
    output_model=BuddySearchQuery,
    system_prompt_template=_BUDDY_SYSTEM_PROMPT,
    examples=_BUDDY_EXAMPLES,
    include_catalog=True,
    catalog_max_size=200,
    catalog_field="interests",
    gate_fields=["interests", "user_references"],
    fetch_catalog=_fetch_buddy_interests,
)


# ---------------------------------------------------------------------------
# Product search domain config
# ---------------------------------------------------------------------------

_PRODUCT_SYSTEM_PROMPT = """\
You are a search query parser for a product marketplace.
Your job is to convert the user's free-text search message into structured search
parameters that the backend can use to find matching products.

EXTRACTION RULES:

1. **Categories** — Extract every product type or category the user mentions.
   - If a catalog of known categories is provided, prefer matching to it.

2. **Brands** — Extract brand names the user explicitly mentions.
   - Only include brands actually stated, do NOT guess.

3. **Price range** — Extract price_min and price_max only when the user states
   a price constraint (e.g. "under $500", "between $50 and $200").
   - If only one bound is mentioned, set the other to null.

4. **Attributes** — Extract specific qualities the user requests
   (color, size, material, wireless, waterproof, etc.).

5. **Empty / ambiguous** — Return empty lists and null prices if nothing
   extractable is found.

OUTPUT FORMAT:
Return valid JSON matching the schema. Every field must be present.
"""

_PRODUCT_EXAMPLES: list[tuple[str, dict[str, Any]]] = [
    (
        "cheap wireless headphones under 100",
        {
            "categories": ["electronics"],
            "brands": [],
            "price_min": None,
            "price_max": 100.0,
            "attributes": ["wireless"],
            "intent_summary": "User wants wireless headphones under $100.",
        },
    ),
    (
        "sony laptop between 500 and 1000 dollars",
        {
            "categories": ["electronics"],
            "brands": ["sony"],
            "price_min": 500.0,
            "price_max": 1000.0,
            "attributes": [],
            "intent_summary": "User wants a Sony laptop in the $500-$1000 price range.",
        },
    ),
]

PRODUCT_SEARCH_DOMAIN = DomainConfig(
    output_model=ProductSearchQuery,
    system_prompt_template=_PRODUCT_SYSTEM_PROMPT,
    examples=_PRODUCT_EXAMPLES,
    include_catalog=True,
    catalog_max_size=200,
    catalog_field="categories",
    gate_fields=["categories", "brands"],
)

DOMAIN_REGISTRY: dict[str, DomainConfig] = {
    "buddy": BUDDY_SEARCH_DOMAIN,
    "product": PRODUCT_SEARCH_DOMAIN,
}


def get_domain_config(domain_name: str) -> DomainConfig:
    if domain_name not in DOMAIN_REGISTRY:
        raise ValueError(f"Unknown search domain: {domain_name}")
    return DOMAIN_REGISTRY[domain_name]

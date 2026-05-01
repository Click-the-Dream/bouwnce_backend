from __future__ import annotations

_INTEREST_SYNONYMS: dict[str, str] = {
    "machine learning": "ai",
    "artificial intelligence": "ai",
    "programming": "coding",
    "software development": "coding",
    "bicycle": "cycling",
    "bike": "cycling",
    "biking": "cycling",
    "road cycling": "cycling",
    "cycling": "cycling",
}


def normalize_interest_name(name: str) -> str:
    normalized = " ".join(name.strip().lower().split())
    return _INTEREST_SYNONYMS.get(normalized, normalized)

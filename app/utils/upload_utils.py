from __future__ import annotations

import re


def split_csv(value: str) -> list[str]:
    return [v.strip().lower() for v in (value or "").split(",") if v.strip()]


def safe_slug_from_filename(file_name: str) -> str:
    name = (file_name or "").strip()
    if not name:
        return ""
    if "." in name:
        name = name.rsplit(".", 1)[0]
    name = name.strip()
    if not name:
        return ""
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:80]

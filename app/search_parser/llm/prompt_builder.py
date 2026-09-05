from __future__ import annotations

import json

from app.search_parser.schemas.schema import DomainConfig


def build_system_prompt(domain: DomainConfig) -> str:
    parts: list[str] = [domain.system_prompt_template]

    model_schema = domain.output_model.model_json_schema()
    properties = model_schema.get("properties", {})
    if properties:
        field_descriptions: list[str] = []
        for field_name, field_info in properties.items():
            desc = field_info.get("description", field_name)
            field_type = field_info.get("type", "string")
            field_descriptions.append(f"- {field_name} ({field_type}): {desc}")
        parts.append("Expected output fields:\n" + "\n".join(field_descriptions))

    return "\n\n".join(parts)


def build_examples_section(domain: DomainConfig) -> str | None:
    if not domain.examples:
        return None

    lines: list[str] = ["Examples:"]
    for user_msg, expected_output in domain.examples:
        lines.append(f'  User: "{user_msg}"')
        lines.append(f"  Output: {json.dumps(expected_output)}")
    return "\n".join(lines)


def build_catalog_section(
    catalog: list[str] | None, domain: DomainConfig
) -> str | None:
    if not catalog:
        return None
    if not domain.include_catalog:
        return None
    if len(catalog) > domain.catalog_max_size:
        return None
    items = ", ".join(catalog)
    return (
        "AVAILABLE INTERESTS (pick from this list ONLY):\n"
        f"{items}\n"
        "IMPORTANT: You must only return interests from the list above. "
        "If the user's request doesn't closely match any entry, pick the "
        "closest semantic match. If nothing is close, return an empty list."
    )


def build_messages(
    message: str,
    domain: DomainConfig,
    catalog: list[str] | None = None,
) -> list[dict[str, str]]:
    system_parts: list[str] = [build_system_prompt(domain)]

    examples_section = build_examples_section(domain)
    if examples_section:
        system_parts.append(examples_section)

    catalog_section = build_catalog_section(catalog, domain)
    if catalog_section:
        system_parts.append(catalog_section)

    system_content = "\n\n".join(system_parts)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": message},
    ]

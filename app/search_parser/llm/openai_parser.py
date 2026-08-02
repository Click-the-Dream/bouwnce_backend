from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.core.config import settings
from app.search_parser.llm.prompt_builder import build_messages
from app.search_parser.schemas.parser import QueryParser
from app.search_parser.schemas.schema import DomainConfig, ParsedQuery
from app.utils.exception import InternalServerErrorException


class OpenAIQueryParser(QueryParser):
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            kwargs = {
                "api_key": settings.OPENAI_API_KEY,
                "timeout": settings.SEARCH_PARSER_LLM_TIMEOUT,
            }
            if settings.OPENAI_BASE_URL:
                kwargs["base_url"] = settings.OPENAI_BASE_URL
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def parse(
        self,
        message: str,
        domain: DomainConfig,
        catalog: list[str] | None = None,
    ) -> ParsedQuery | None:
        if not message.strip():
            return None

        messages = build_messages(message, domain, catalog)

        schema = domain.output_model.model_json_schema()
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": domain.output_model.__name__,
                "schema": schema,
                "strict": True,
            },
        }

        try:
            print(f"parse request: message={message[:100]!r}")
            response = await self.client.chat.completions.create(
                model=settings.SEARCH_PARSER_LLM_MODEL,
                messages=messages,
                response_format=response_format,
                temperature=0.0,
                max_tokens=512,
            )
            print(
                f"parse response: finish_reason={response.choices[0].finish_reason if response.choices else None}"
            )
        except Exception as exc:
            InternalServerErrorException
            return None

        content = response.choices[0].message.content
        if not content:
            print("[llm] returned empty content")
            return None

        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            print(f"[llm] returned invalid JSON: {content[:200]}")
            return None

        try:
            validated = domain.output_model.model_validate(raw)
        except Exception:
            print(f"[llm] output failed schema validation: {content[:200]}")
            return None

        print(
            f"[llm] parse success: fields={list(validated.model_dump().keys())} parsed={validated.model_dump()}"
        )

        return ParsedQuery(
            fields=validated.model_dump(),
            raw_message=message,
            source="llm",
        )

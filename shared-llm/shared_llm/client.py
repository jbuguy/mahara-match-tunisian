from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class LLMSettings:
    base_url: str = "http://localhost:1234/v1"
    model: str = "local-model"
    api_key: str | None = None
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "LLMSettings":
        return cls(
            base_url=os.getenv("LLM_BASE_URL", cls.base_url).rstrip("/"),
            model=os.getenv("LLM_MODEL", cls.model),
            api_key=os.getenv("LLM_API_KEY"),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        )


class LLMError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        settings: LLMSettings | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self._http_client = http_client or httpx.AsyncClient(timeout=self.settings.timeout_seconds)
        self._owns_http_client = http_client is None

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def complete_chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: dict[str, str] | None = None,
        temperature: float = 0.2,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        try:
            response = await self._http_client.post(
                f"{self.settings.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMError("The configured LLM endpoint did not return a valid chat completion") from error

        if not isinstance(content, str) or not content.strip():
            raise LLMError("The configured LLM endpoint returned an empty completion")
        return content.strip()
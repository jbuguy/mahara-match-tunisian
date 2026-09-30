import asyncio
import json

import httpx
import pytest

from shared_llm import LLMError, LLMSettings, OpenAICompatibleClient


def test_client_sends_configured_model_and_json_mode():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": " {\"ok\": true} "}}]})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleClient(
        LLMSettings(base_url="http://lm-studio.test/v1", model="qwen-local"),
        http_client=http_client,
    )

    try:
        content = asyncio.run(
            client.complete_chat(
                [{"role": "user", "content": "hello"}],
                response_format={"type": "json_object"},
            )
        )
    finally:
        asyncio.run(http_client.aclose())

    assert content == '{"ok": true}'
    assert captured["url"] == "http://lm-studio.test/v1/chat/completions"
    assert captured["payload"]["model"] == "qwen-local"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["chat_template_kwargs"] == {"enable_thinking": False}


def test_client_wraps_http_errors():
    http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503, text="offline"))
    )
    client = OpenAICompatibleClient(LLMSettings(), http_client=http_client)

    try:
        with pytest.raises(LLMError, match="did not return a valid chat completion"):
            asyncio.run(client.complete_chat([{"role": "user", "content": "hello"}]))
    finally:
        asyncio.run(http_client.aclose())


def test_settings_read_local_endpoint_and_model_from_environment(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1/")
    monkeypatch.setenv("LLM_MODEL", "loaded-model")

    settings = LLMSettings.from_env()

    assert settings.base_url == "http://127.0.0.1:1234/v1"
    assert settings.model == "loaded-model"
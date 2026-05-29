"""Provider adapters for Ollama-compatible and Atlas Cloud backends."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
import ollama


ATLAS_BASE_URL = "https://api.atlascloud.ai/v1"
ATLAS_KEY_ENV_VARS = ("ATLAS_API_KEY", "ATLASCLOUD_API_KEY")
ATLAS_LOCAL_CONFIG = os.path.expanduser("~/.config/ollmcp/atlascloud.json")


class ProviderResponseError(Exception):
    """Provider-agnostic response error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ProviderFunctionCall:
    """Normalized tool function call."""

    name: str
    arguments: Dict[str, Any]


@dataclass
class ProviderToolCall:
    """Normalized tool call."""

    id: Optional[str]
    function: ProviderFunctionCall


@dataclass
class ProviderMessage:
    """Normalized chat message chunk."""

    content: str = ""
    thinking: str = ""
    tool_calls: List[ProviderToolCall] = field(default_factory=list)


@dataclass
class ProviderChunk:
    """Normalized streaming chunk."""

    message: ProviderMessage
    done: bool = False
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


def is_atlascloud_host(host: Optional[str]) -> bool:
    """Return True when the configured host points to Atlas Cloud."""
    if not host:
        return False
    normalized = host.rstrip("/").lower()
    return "atlascloud.ai" in normalized


def build_llm_client(host: str):
    """Build the appropriate async client for the configured host."""
    if is_atlascloud_host(host):
        return AtlasCloudAsyncClient(base_url=host)
    return OllamaAsyncClient(host=host)


def get_provider_name_for_host(host: Optional[str]) -> str:
    """Return a human-readable provider name for the configured host."""
    return "Atlas Cloud" if is_atlascloud_host(host) else "Ollama"


def load_atlas_api_key() -> Optional[str]:
    """Load Atlas API key from env vars or local config file."""
    for env_var in ATLAS_KEY_ENV_VARS:
        value = os.getenv(env_var)
        if value:
            return value.strip()

    try:
        with open(ATLAS_LOCAL_CONFIG, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None

    value = data.get("apiKey")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


class OllamaAsyncClient:
    """Thin wrapper around the Ollama async client."""

    def __init__(self, host: str):
        self.host = host
        self._client = ollama.AsyncClient(host=host)

    async def list(self):
        return await self._client.list()

    async def show(self, model_name: str):
        return await self._client.show(model_name)

    async def chat(self, **kwargs):
        return await self._client.chat(**kwargs)


class AtlasCloudAsyncClient:
    """Minimal OpenAI-compatible Atlas Cloud adapter."""

    def __init__(self, base_url: str = ATLAS_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._models_cache: Dict[str, Dict[str, Any]] = {}

    def _headers(self) -> Dict[str, str]:
        api_key = load_atlas_api_key()
        if not api_key:
            raise ProviderResponseError(
                "Atlas Cloud API key not found. Set ATLAS_API_KEY or save ~/.config/ollmcp/atlascloud.json."
            )
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def list(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/models", headers=self._headers())
        data = self._ensure_success(response)
        raw_models = data.get("data", [])
        models = []
        self._models_cache = {}
        for item in raw_models:
            model_name = item.get("id") or item.get("name")
            if not model_name:
                continue
            model_info = {
                "name": model_name,
                "model": model_name,
                "size": 0,
                "modified_at": "Unknown",
                "context_length": item.get("context_length"),
            }
            self._models_cache[model_name] = item
            models.append(model_info)
        return {"models": models}

    async def show(self, model_name: str) -> Dict[str, Any]:
        if not self._models_cache:
            try:
                await self.list()
            except ProviderResponseError:
                # Keep capability lookup best-effort; caller already handles failures.
                pass

        raw = self._models_cache.get(model_name, {})
        return {
            "name": model_name,
            "context_length": raw.get("context_length"),
            "capabilities": self._infer_capabilities(model_name),
        }

    async def chat(self, **kwargs) -> AsyncIterator[ProviderChunk]:
        stream = bool(kwargs.get("stream"))
        payload = self._build_chat_payload(kwargs)
        url = f"{self.base_url}/chat/completions"

        if not stream:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, headers=self._headers(), json=payload)
            data = self._ensure_success(response)
            return self._single_response_stream(data)

        return self._streaming_response(url, payload)

    def _single_response_stream(self, data: Dict[str, Any]) -> AsyncIterator[ProviderChunk]:
        async def _iterator():
            choice = (data.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            yield ProviderChunk(
                message=ProviderMessage(
                    content=message.get("content") or "",
                    tool_calls=self._convert_tool_calls(message.get("tool_calls")),
                ),
                done=True,
                prompt_eval_count=((data.get("usage") or {}).get("prompt_tokens")),
                eval_count=((data.get("usage") or {}).get("completion_tokens")),
            )

        return _iterator()

    async def _streaming_response(self, url: str, payload: Dict[str, Any]) -> AsyncIterator[ProviderChunk]:
        started_at = time.monotonic()
        tool_call_parts: Dict[int, Dict[str, Any]] = {}
        usage: Dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=30.0)) as client:
            async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise self._error_from_body(response.status_code, body.decode("utf-8", errors="ignore"))

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    raw_payload = line[6:].strip()
                    if raw_payload == "[DONE]":
                        break

                    chunk_data = json.loads(raw_payload)
                    if "usage" in chunk_data:
                        usage = chunk_data.get("usage") or {}

                    choices = chunk_data.get("choices") or []
                    if not choices:
                        continue

                    choice = choices[0]
                    delta = choice.get("delta") or {}
                    finish_reason = choice.get("finish_reason")

                    content = delta.get("content") or ""
                    if content:
                        yield ProviderChunk(message=ProviderMessage(content=content))

                    if delta.get("tool_calls"):
                        self._merge_tool_call_delta(tool_call_parts, delta["tool_calls"])

                    if finish_reason == "tool_calls" and tool_call_parts:
                        yield ProviderChunk(
                            message=ProviderMessage(tool_calls=self._finalize_tool_calls(tool_call_parts))
                        )
                        tool_call_parts = {}

        total_duration = int((time.monotonic() - started_at) * 1_000_000_000)
        if tool_call_parts:
            yield ProviderChunk(message=ProviderMessage(tool_calls=self._finalize_tool_calls(tool_call_parts)))

        yield ProviderChunk(
            message=ProviderMessage(),
            done=True,
            total_duration=total_duration,
            prompt_eval_count=usage.get("prompt_tokens"),
            eval_count=usage.get("completion_tokens"),
        )

    def _build_chat_payload(self, chat_params: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": chat_params["model"],
            "messages": self._convert_messages(chat_params.get("messages") or []),
            "stream": bool(chat_params.get("stream")),
        }

        tools = chat_params.get("tools") or []
        if tools:
            payload["tools"] = tools

        options = chat_params.get("options") or {}
        option_mappings = {
            "temperature": "temperature",
            "top_p": "top_p",
            "presence_penalty": "presence_penalty",
            "frequency_penalty": "frequency_penalty",
            "seed": "seed",
            "stop": "stop",
            "num_predict": "max_tokens",
        }
        for source_key, target_key in option_mappings.items():
            value = options.get(source_key)
            if value is not None:
                payload[target_key] = value

        if payload["stream"]:
            payload["stream_options"] = {"include_usage": True}

        return payload

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted = []
        for message in messages:
            converted_message = {
                "role": message["role"],
            }

            content = message.get("content")
            if isinstance(content, list):
                converted_message["content"] = content
            else:
                converted_message["content"] = content or ""

            if "tool_calls" in message and message["tool_calls"]:
                converted_message["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": json.dumps(tool_call.function.arguments),
                        },
                    }
                    for tool_call in message["tool_calls"]
                ]

            if message["role"] == "tool":
                tool_call_id = message.get("tool_call_id")
                if tool_call_id:
                    converted_message["tool_call_id"] = tool_call_id
                elif message.get("tool_name"):
                    converted_message["name"] = message["tool_name"]

            if message.get("images"):
                converted_message["content"] = [
                    {"type": "text", "text": content or ""},
                    *[
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image}"}}
                        for image in message["images"]
                    ],
                ]

            converted.append(converted_message)
        return converted

    def _convert_tool_calls(self, tool_calls: Optional[List[Dict[str, Any]]]) -> List[ProviderToolCall]:
        if not tool_calls:
            return []
        converted = []
        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            converted.append(
                ProviderToolCall(
                    id=tool_call.get("id"),
                    function=ProviderFunctionCall(
                        name=function.get("name", ""),
                        arguments=arguments if isinstance(arguments, dict) else {},
                    ),
                )
            )
        return converted

    def _merge_tool_call_delta(self, tool_call_parts: Dict[int, Dict[str, Any]], items: List[Dict[str, Any]]) -> None:
        for item in items:
            index = item.get("index", 0)
            current = tool_call_parts.setdefault(
                index,
                {"id": None, "name": "", "arguments": ""},
            )
            if item.get("id"):
                current["id"] = item["id"]

            function = item.get("function") or {}
            if function.get("name"):
                current["name"] = function["name"]
            if function.get("arguments"):
                current["arguments"] += function["arguments"]

    def _finalize_tool_calls(self, tool_call_parts: Dict[int, Dict[str, Any]]) -> List[ProviderToolCall]:
        finalized = []
        for index in sorted(tool_call_parts):
            item = tool_call_parts[index]
            arguments = item["arguments"]
            try:
                parsed_arguments = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                parsed_arguments = {}
            finalized.append(
                ProviderToolCall(
                    id=item.get("id"),
                    function=ProviderFunctionCall(
                        name=item.get("name", ""),
                        arguments=parsed_arguments,
                    ),
                )
            )
        return finalized

    def _infer_capabilities(self, model_name: str) -> List[str]:
        name = model_name.lower()
        capabilities = ["tools"]
        if re.search(r"(vision|vl|gpt-4o|gpt-4\.1|gemini|claude|glm-5v)", name):
            capabilities.append("vision")
        if re.search(r"(thinking|reason|r1|o1|o3|o4)", name):
            capabilities.append("thinking")
        return capabilities

    def _ensure_success(self, response: httpx.Response) -> Dict[str, Any]:
        if response.status_code >= 400:
            raise self._error_from_body(response.status_code, response.text)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise ProviderResponseError(f"Atlas Cloud returned invalid JSON: {exc}") from exc

        if isinstance(data, dict) and data.get("code") not in (None, 200):
            raise ProviderResponseError(
                f"Atlas Cloud request failed: {data.get('msg', 'unknown error')}",
                status_code=response.status_code,
            )
        return data

    def _error_from_body(self, status_code: int, body: str) -> ProviderResponseError:
        message = body.strip()
        try:
            data = json.loads(message)
            if isinstance(data, dict):
                if "error" in data and isinstance(data["error"], dict):
                    message = data["error"].get("message") or message
                elif data.get("msg"):
                    message = data["msg"]
        except json.JSONDecodeError:
            pass
        return ProviderResponseError(f"Atlas Cloud error ({status_code}): {message}", status_code=status_code)

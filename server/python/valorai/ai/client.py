"""Provider-agnostic OpenAI-Compatible Chat Completions client."""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

HttpPostFn = Callable[[str, dict[str, str], str, float], tuple[int, str]]


class AiProviderError(Exception):
    """Raised when the AI provider fails or returns an invalid payload."""


class AiRateLimitError(AiProviderError):
    """Raised when the AI provider returns HTTP 429."""


@dataclass(frozen=True)
class AiConfig:
    mode: str = "demo"  # "openai_compatible" | "demo"
    base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    api_key: str | None = None
    model: str = "gemini-3.5-flash-lite"
    tier: str = "free_prototype"  # "free_prototype" | "paid"

    @property
    def enabled(self) -> bool:
        return self.mode == "openai_compatible" and bool((self.api_key or "").strip()) and bool(self.base_url.strip())


def _urllib_post(url: str, headers: dict[str, str], body: str, timeout_s: float) -> tuple[int, str]:
    req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", errors="replace")


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text


class OpenAiCompatibleClient:
    """Synchronous client compatible with OpenAI Chat Completions (e.g., Gemini OpenAI endpoint)."""

    def __init__(self, config: AiConfig, http_post: HttpPostFn | None = None):
        self.config = config
        self.http_post = http_post or _urllib_post

    def is_configured(self) -> bool:
        return self.config.enabled

    def chat_json(
        self,
        messages: list[dict],
        json_schema: dict | None = None,
        schema_name: str = "response",
        timeout_s: float = 8.0,
    ) -> dict:
        if not self.is_configured():
            raise AiProviderError("AI provider is not configured.")

        endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload: dict = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema,
                },
            }
        else:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        status, text = self.http_post(endpoint, headers, json.dumps(payload, ensure_ascii=False), timeout_s)
        if status == 429:
            raise AiRateLimitError("AI provider rate limit exceeded (429).")
        if status < 200 or status >= 300:
            raise AiProviderError(f"AI provider returned HTTP {status}.")

        try:
            envelope = json.loads(text)
            content = envelope["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            parsed = json.loads(_strip_code_fences(str(content)))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AiProviderError("Invalid JSON response from AI provider.") from exc

        if not isinstance(parsed, dict):
            raise AiProviderError("Expected a JSON object from AI provider.")
        return parsed

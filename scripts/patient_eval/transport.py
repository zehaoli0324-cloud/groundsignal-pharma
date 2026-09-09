"""Bounded, explicit chat-completions transport for interactive studies.

Constructing a client validates configuration and credential presence; it does
not make a request. Only calling it sends visible role/content messages. API
keys and response error bodies are never included in returned audit records.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from .adapters import NoRedirect
from .contracts import require


class ChatClient:
    def __init__(self, base_url: str, model: str, key_env: str, timeout: float = 30,
                 retries: int = 1, max_tokens: int = 800, temperature: float = 0):
        require(isinstance(base_url, str), "base_url must be text")
        parsed = urllib.parse.urlparse(base_url)
        require(parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}),
                "base URL must use HTTPS except local development")
        require(bool(parsed.hostname) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
                "base URL must not contain credentials/query/fragment")
        require(isinstance(model, str) and bool(model.strip()), "model is required")
        require(isinstance(key_env, str) and bool(key_env.strip()), "key_env is required")
        require(type(timeout) in {float, int} and 0 < timeout <= 120, "timeout out of bounds")
        require(type(retries) is int and 0 <= retries <= 2, "retries out of bounds")
        require(type(max_tokens) is int and 1 <= max_tokens <= 8192, "max_tokens out of bounds")
        require(type(temperature) in {float, int} and 0 <= temperature <= 2, "temperature out of bounds")
        key = os.environ.get(key_env)
        require(bool(key), "missing credential environment variable: " + key_env)
        self._key = key
        self.model = model
        self.platform = parsed.hostname + "/" + model
        self._base_url = base_url.rstrip("/")
        self.timeout, self.retries = timeout, retries
        self.max_tokens, self.temperature = max_tokens, temperature
        self._opener = urllib.request.build_opener(NoRedirect())

    def public_config(self) -> dict:
        return {"transport": "chat_completions/v0.2", "base_url": self._base_url,
                "model": self.model, "timeout": self.timeout, "retries": self.retries,
                "max_tokens": self.max_tokens, "temperature": self.temperature}

    def __call__(self, messages: list[dict]) -> dict:
        require(isinstance(messages, list) and bool(messages), "messages must be nonempty")
        visible = []
        for message in messages:
            require(isinstance(message, dict) and set(message) == {"role", "content"},
                    "messages must contain role/content only")
            require(message["role"] in {"system", "user", "assistant"}, "unsupported role")
            require(isinstance(message["content"], str) and bool(message["content"].strip()), "empty message")
            visible.append(dict(message))
        payload = {"model": self.model, "messages": visible, "temperature": self.temperature, "max_tokens": self.max_tokens}
        request = urllib.request.Request(self._base_url + "/chat/completions",
                                        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                        headers={"Authorization": "Bearer " + self._key, "Content-Type": "application/json"})
        attempts, content, usage = [], None, {}
        for index in range(self.retries + 1):
            start, retryable, error = time.monotonic(), False, None
            try:
                with self._opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(2_000_001)
                require(len(raw) <= 2_000_000, "response too large")
                result = json.loads(raw)
                content = result["choices"][0]["message"]["content"]
                require(isinstance(content, str) and bool(content.strip()), "empty response content")
                returned_usage = result.get("usage", {})
                if isinstance(returned_usage, dict):
                    usage = {key: value for key, value in returned_usage.items()
                             if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                             and type(value) is int and value >= 0}
            except urllib.error.HTTPError as exc:
                error = "http_" + str(exc.code)
                retryable = exc.code == 429 or 500 <= exc.code < 600
            except (urllib.error.URLError, TimeoutError, OSError):
                error, retryable = "transport_error", True
            except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
                error = "invalid_response_schema"
            attempts.append({"attempt": index + 1, "elapsed_seconds": round(time.monotonic() - start, 6), "error": error})
            if error is None or not retryable or index == self.retries:
                break
            time.sleep(min(0.25 * 2 ** index, 1))
        error = attempts[-1]["error"]
        return {"content": content if error is None else None, "error": error,
                "attempts": attempts, "usage": usage if error is None else {}}

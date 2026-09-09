"""Explicitly invoked chat-completions adapter. Never called by demo or tests.

Only visible prefix text reaches the service. Network retries are bounded; a
service error remains a target failure rather than disappearing from metrics.
No response text is automatically judged for clinical correctness.
"""

from __future__ import annotations

import copy
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .contracts import require, validate_session, visible_prefix
from .runner import digest


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a bearer credential to a redirect target.


def run_api(scenario: dict, *, base_url: str, model: str, key_env: str,
            timeout: float = 30, retries: int = 1, temperature: float = 0) -> dict:
    messages = visible_prefix(scenario)
    require(bool(model.strip()), "model is required")
    require(0 < timeout <= 120 and 0 <= retries <= 2, "timeout/retries out of bounds")
    parsed = urllib.parse.urlparse(base_url)
    require(parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}),
            "base URL must use HTTPS (except local development)")
    require(bool(parsed.hostname) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,
            "base URL must not contain credentials/query/fragment")
    key = os.environ.get(key_env)
    require(bool(key), f"missing credential environment variable: {key_env}")
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": 800}
    request = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                     data=json.dumps(payload, ensure_ascii=False).encode(),
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    opener = urllib.request.build_opener(NoRedirect())
    attempts = []
    content = None
    for attempt in range(retries + 1):
        start = time.monotonic()
        retryable = False
        try:
            with opener.open(request, timeout=timeout) as response:
                raw = response.read(2_000_001)
            require(len(raw) <= 2_000_000, "response too large")
            result = json.loads(raw)
            content = result["choices"][0]["message"]["content"]
            require(isinstance(content, str) and bool(content.strip()), "empty response content")
            error = None
        except urllib.error.HTTPError as exc:
            error = f"http_{exc.code}"
            retryable = exc.code == 429 or 500 <= exc.code < 600
        except (urllib.error.URLError, TimeoutError, OSError):
            error, retryable = "transport_error", True
        except (ValueError, KeyError, IndexError, TypeError):
            error = "invalid_response_schema"
        attempts.append({"attempt": attempt + 1, "elapsed_seconds": round(time.monotonic() - start, 6), "error": error})
        if error is None or not retryable or attempt == retries:
            break
        time.sleep(min(0.25 * 2 ** attempt, 1))
    turns = copy.deepcopy(scenario["prefix"])
    if attempts[-1]["error"] is None:
        turns.append({"turn_id": "answer", "role": "assistant", "content": content})
    session = {
        "session_id": scenario["scenario_id"] + ":api:" + digest({"model": model, "time": time.time_ns()})[:12],
        "scenario_id": scenario["scenario_id"], "family_id": scenario["family_id"], "variant": scenario["variant"],
        "platform": parsed.hostname + "/" + model, "observability": "black_box",
        "status": "completed" if attempts[-1]["error"] is None else "target_error",
        "turns": turns, "observations": [], "trace": [],
        "metadata": {"collected_at": datetime.now(timezone.utc).isoformat(), "app_version": "API:model=" + model,
                     "platform_mode": "chat_completions", "conversation_reset": True, "input_mode": "text",
                     "comparison_lane": "fixed_prefix", "question_source": scenario["source"],
                     "deidentification_confirmed": scenario["source"] == "synthetic" or scenario.get("deidentification_confirmed") is True,
                     "use_authorized": scenario["source"] == "synthetic" or scenario.get("use_authorized") is True,
                     "session_protocol_id": scenario["protocol_id"], "operator": "api_adapter",
                     "model": model, "temperature": temperature, "max_tokens": 800, "attempts": attempts,
                     "prefix_sha256": digest(scenario["prefix"]), "scenario_sha256": digest(scenario),
                     "clinical_approval": False},
    }
    validate_session(session)
    return session

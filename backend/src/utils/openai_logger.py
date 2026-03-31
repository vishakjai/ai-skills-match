import json
import logging
import os
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Paths – logs live under  backend/logs/
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_RAW_LOG_PATH = os.path.join(_LOG_DIR, "openai_raw.log")
_FMT_LOG_PATH = os.path.join(_LOG_DIR, "openai_formatted.log")

# ---------------------------------------------------------------------------
# Raw logger  – JSON-lines, one object per API call
# ---------------------------------------------------------------------------
_raw_logger = logging.getLogger("openai.raw")
_raw_logger.setLevel(logging.DEBUG)
_raw_logger.propagate = False
_raw_handler = RotatingFileHandler(_RAW_LOG_PATH, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
_raw_handler.setFormatter(logging.Formatter("%(message)s"))
_raw_logger.addHandler(_raw_handler)

# ---------------------------------------------------------------------------
# Formatted logger – human-readable, timestamped
# ---------------------------------------------------------------------------
_fmt_logger = logging.getLogger("openai.formatted")
_fmt_logger.setLevel(logging.DEBUG)
_fmt_logger.propagate = False
_fmt_handler = RotatingFileHandler(_FMT_LOG_PATH, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
_fmt_handler.setFormatter(logging.Formatter("%(message)s"))
_fmt_logger.addHandler(_fmt_handler)


def _safe_serialize(obj: Any) -> Any:
    """Convert Pydantic models / arbitrary objects to JSON-safe dicts."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(i) for i in obj]
    # Pydantic v2
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    # Pydantic v1
    if hasattr(obj, "dict"):
        return obj.dict()
    # OpenAI response objects
    if hasattr(obj, "__dict__"):
        return {k: _safe_serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


def _truncate(text: str, max_len: int = 4000) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... [truncated, total {len(text)} chars]"


class OpenAICallTimer:
    """Context-manager that records wall-clock time for an OpenAI call and
    writes to both log files when ``finish()`` is called."""

    def __init__(self, operation: str, model: str, messages: list, extra: Optional[dict] = None):
        self.operation = operation
        self.model = model
        self.messages = messages
        self.extra = extra or {}
        self._start = time.perf_counter()
        self._timestamp = datetime.now().astimezone().isoformat()

    # ------------------------------------------------------------------
    # Call this after you receive the OpenAI response
    # ------------------------------------------------------------------
    def finish(self, response: Any = None, error: Optional[Exception] = None):
        elapsed_ms = round((time.perf_counter() - self._start) * 1000, 1)

        # ---- extract usage if available ----
        usage = {}
        if response and hasattr(response, "usage") and response.usage:
            u = response.usage
            usage = {
                "prompt_tokens": getattr(u, "prompt_tokens", None),
                "completion_tokens": getattr(u, "completion_tokens", None),
                "total_tokens": getattr(u, "total_tokens", None),
            }

        # ---- extract parsed result ----
        parsed = None
        if response and hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            if hasattr(msg, "parsed") and msg.parsed is not None:
                parsed = _safe_serialize(msg.parsed)
            elif hasattr(msg, "content"):
                parsed = msg.content

        # ======== RAW LOG (JSON-lines) ========
        raw_entry = {
            "timestamp": self._timestamp,
            "operation": self.operation,
            "model": self.model,
            "elapsed_ms": elapsed_ms,
            "request": {
                "messages": _safe_serialize(self.messages),
                **{k: _safe_serialize(v) for k, v in self.extra.items()},
            },
            "response": {
                "usage": usage,
                "parsed": parsed,
            },
            "error": str(error) if error else None,
        }
        raw_separator = "=" * 80
        _raw_logger.debug(f"\n{raw_separator}\n{json.dumps(raw_entry, indent=2, default=str, ensure_ascii=False)}\n{raw_separator}")

        # ======== FORMATTED LOG ========
        separator = "=" * 80
        lines = [
            separator,
            f"  TIMESTAMP   : {self._timestamp}",
            f"  OPERATION   : {self.operation}",
            f"  MODEL       : {self.model}",
            f"  LATENCY     : {elapsed_ms} ms",
        ]

        if usage:
            lines.append(f"  TOKENS      : prompt={usage.get('prompt_tokens')}  completion={usage.get('completion_tokens')}  total={usage.get('total_tokens')}")

        if error:
            lines.append(f"  ERROR       : {error}")

        # Request summary
        lines.append("")
        lines.append("  --- REQUEST (messages) ---")
        for msg in self.messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            lines.append(f"  [{role}] {_truncate(content, 1000)}")

        # Response summary
        lines.append("")
        lines.append("  --- RESPONSE (parsed) ---")
        if parsed:
            pretty = json.dumps(parsed, indent=2, default=str, ensure_ascii=False)
            # Cap formatted output at 20000 chars
            lines.append(f"  {_truncate(pretty, 20000)}")
        else:
            lines.append("  (no parsed response)")

        lines.append(separator)
        _fmt_logger.debug("\n".join(lines))

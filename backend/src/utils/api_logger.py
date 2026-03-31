"""
Middleware that logs every API request and response to backend/logs/api_requests.log
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ---------------------------------------------------------------------------
# Log file setup
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_API_RAW_PATH = os.path.join(_LOG_DIR, "api_requests_raw.log")
_API_FMT_PATH = os.path.join(_LOG_DIR, "api_requests.log")

# Raw logger (JSON-lines)
_raw_logger = logging.getLogger("api.raw")
_raw_logger.setLevel(logging.DEBUG)
_raw_logger.propagate = False
_raw_h = RotatingFileHandler(_API_RAW_PATH, maxBytes=20_000_000, backupCount=5, encoding="utf-8")
_raw_h.setFormatter(logging.Formatter("%(message)s"))
_raw_logger.addHandler(_raw_h)

# Formatted logger (human-readable)
_fmt_logger = logging.getLogger("api.formatted")
_fmt_logger.setLevel(logging.DEBUG)
_fmt_logger.propagate = False
_fmt_h = RotatingFileHandler(_API_FMT_PATH, maxBytes=20_000_000, backupCount=5, encoding="utf-8")
_fmt_h.setFormatter(logging.Formatter("%(message)s"))
_fmt_logger.addHandler(_fmt_h)


def _truncate(text: str, max_len: int = 2000) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... [truncated, total {len(text)} chars]"


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, default=str, ensure_ascii=False)
    except Exception:
        return str(obj)


# Paths we skip logging body for (file uploads produce huge bodies)
_SKIP_REQUEST_BODY = {"/batch/upload", "/utils/parse_doc", "/extract/resume/file", "/extract/jd/file", "/upload-cvs"}
# Paths we skip logging entirely (noisy health checks, etc.)
_SKIP_ENTIRELY = {"/health", "/favicon.ico"}
# Content types where we capture the request body
_JSON_TYPES = {"application/json"}

# Max body size to capture (bytes)
_MAX_BODY_CAPTURE = 50_000


class APIRequestLogger(BaseHTTPMiddleware):
    """Logs method, path, headers, request body, response status, response body, and timing."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip noisy endpoints
        if path in _SKIP_ENTIRELY:
            return await call_next(request)

        start = time.perf_counter()
        ts = datetime.now().astimezone().isoformat()

        method = request.method
        query = str(request.url.query) if request.url.query else ""
        client = request.client.host if request.client else "unknown"

        # --- Capture select headers ---
        headers_of_interest = {}
        for key in ("x-user-name", "content-type", "content-length"):
            val = request.headers.get(key)
            if val:
                headers_of_interest[key] = val

        # --- Capture request body (JSON only, skip file uploads) ---
        req_body_str = None
        content_type = request.headers.get("content-type", "")

        is_file_upload = any(skip in path for skip in _SKIP_REQUEST_BODY) or "multipart" in content_type
        is_json = any(ct in content_type for ct in _JSON_TYPES)

        if is_json and not is_file_upload:
            try:
                raw = await request.body()
                if len(raw) <= _MAX_BODY_CAPTURE:
                    req_body_str = raw.decode("utf-8", errors="ignore")
                else:
                    req_body_str = f"[body too large: {len(raw)} bytes]"
            except Exception:
                req_body_str = "[could not read body]"
        elif is_file_upload:
            req_body_str = f"[file upload, content-type: {content_type}]"

        # --- Call the actual endpoint ---
        resp_body_bytes = b""
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code

            # Capture response body by consuming the stream and re-wrapping
            chunks = []
            async for chunk in response.body_iterator:
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                chunks.append(chunk)
            resp_body_bytes = b"".join(chunks)

            # Re-create response with the consumed body
            response = Response(
                content=resp_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            _log_entry(ts, method, path, query, client, headers_of_interest,
                       req_body_str, 500, None, elapsed_ms, error=str(exc))
            raise

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

        # Decode response body for logging
        resp_body_str = None
        try:
            if len(resp_body_bytes) <= _MAX_BODY_CAPTURE:
                resp_body_str = resp_body_bytes.decode("utf-8", errors="ignore")
            else:
                resp_body_str = f"[response too large: {len(resp_body_bytes)} bytes]"
        except Exception:
            resp_body_str = "[could not decode response]"

        _log_entry(ts, method, path, query, client, headers_of_interest,
                   req_body_str, status_code, resp_body_str, elapsed_ms)

        return response


def _log_entry(
    ts: str, method: str, path: str, query: str, client: str,
    headers: dict, req_body: Optional[str], status: int,
    resp_body: Optional[str], elapsed_ms: float, error: Optional[str] = None,
):
    # ---- RAW (JSON-lines) ----
    raw = {
        "timestamp": ts,
        "method": method,
        "path": path,
        "query": query,
        "client": client,
        "headers": headers,
        "request_body": req_body,
        "status": status,
        "response_body": resp_body,
        "elapsed_ms": elapsed_ms,
        "error": error,
    }
    sep = "=" * 80
    _raw_logger.debug(f"\n{sep}\n{_safe_json(raw)}\n{sep}")

    # ---- FORMATTED ----
    lines = [
        sep,
        f"  {method} {path}{'?' + query if query else ''}  →  {status}  ({elapsed_ms} ms)",
        f"  TIME   : {ts}",
        f"  CLIENT : {client}",
    ]
    if headers:
        lines.append(f"  HEADERS: {headers}")
    if error:
        lines.append(f"  ERROR  : {error}")

    # Request body (truncated)
    if req_body:
        lines.append("")
        lines.append("  --- REQUEST BODY ---")
        # Try to pretty-print JSON
        try:
            parsed = json.loads(req_body)
            lines.append(f"  {_truncate(_safe_json(parsed), 3000)}")
        except Exception:
            lines.append(f"  {_truncate(req_body, 3000)}")

    # Response body (truncated)
    if resp_body:
        lines.append("")
        lines.append("  --- RESPONSE BODY ---")
        try:
            parsed = json.loads(resp_body)
            lines.append(f"  {_truncate(_safe_json(parsed), 3000)}")
        except Exception:
            lines.append(f"  {_truncate(resp_body, 3000)}")

    lines.append(sep)
    _fmt_logger.debug("\n".join(lines))

"""
Shared wire utilities for hosted-API architectures.

Every provider API CLAIA speaks (OpenAI Responses, Anthropic Messages,
OpenAI-compatible chat completions) streams server-sent events as
``data: <json>`` lines with a ``[DONE]`` sentinel, and reports errors
as a ``{message, code/type}`` object. These helpers own that shared
wire so each architecture only handles its provider's event shapes.
"""

import json
import logging
from typing import Any, Dict, Iterator, Optional

from ...data.chunks import UsageChunk


logger = logging.getLogger(__name__)


def _as_int(value: Any) -> Optional[int]:
  if value is None:
    return None
  try:
    return int(value)
  except (TypeError, ValueError):
    return None


def _nested_int(payload: Dict[str, Any], *keys: str) -> Optional[int]:
  current: Any = payload
  for key in keys:
    if not isinstance(current, dict):
      return None
    current = current.get(key)
  return _as_int(current)


def usage_chunk(
  payload: Optional[Dict[str, Any]],
  *,
  provider: str,
  provider_model: str,
  finish_reason: Optional[str] = None,
) -> Optional[UsageChunk]:
  """Map a provider usage blob into a ``UsageChunk``.

  Accepts OpenAI-style (``prompt_tokens`` / ``completion_tokens``) and
  Anthropic/Responses-style (``input_tokens`` / ``output_tokens``)
  field names. Returns ``None`` when there is nothing real to report.
  """
  if not payload and not finish_reason:
    return None

  raw = payload if isinstance(payload, dict) else {}
  prompt_tokens = _as_int(raw.get("prompt_tokens") if raw.get("prompt_tokens") is not None else raw.get("input_tokens"))
  completion_tokens = _as_int(
    raw.get("completion_tokens") if raw.get("completion_tokens") is not None else raw.get("output_tokens")
  )
  total_tokens = _as_int(raw.get("total_tokens"))
  if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
    total_tokens = prompt_tokens + completion_tokens

  cached_tokens = (
    _as_int(raw.get("cached_tokens"))
    or _as_int(raw.get("cache_read_input_tokens"))
    or _nested_int(raw, "prompt_tokens_details", "cached_tokens")
    or _nested_int(raw, "input_tokens_details", "cached_tokens")
  )
  reasoning_tokens = (
    _as_int(raw.get("reasoning_tokens"))
    or _nested_int(raw, "completion_tokens_details", "reasoning_tokens")
    or _nested_int(raw, "output_tokens_details", "reasoning_tokens")
  )

  if (
    prompt_tokens is None
    and completion_tokens is None
    and total_tokens is None
    and cached_tokens is None
    and reasoning_tokens is None
    and not finish_reason
  ):
    return None

  return UsageChunk(
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    total_tokens=total_tokens,
    cached_tokens=cached_tokens,
    reasoning_tokens=reasoning_tokens,
    finish_reason=finish_reason,
    provider=provider,
    provider_model=provider_model,
    metadata={"raw": raw} if raw else None,
  )


def iter_sse(response) -> Iterator[Dict[str, Any]]:
  """Yield decoded JSON payloads from an SSE response.

  Skips blank/comment lines and undecodable payloads; stops at the
  ``[DONE]`` sentinel or end of stream.
  """
  for line in response.iter_lines():
    if not line:
      continue
    text = line.decode("utf-8") if isinstance(line, bytes) else line
    if not text.startswith("data: "):
      continue
    payload = text[6:]
    if payload.strip() == "[DONE]":
      return
    try:
      yield json.loads(payload)
    except json.JSONDecodeError:
      logger.debug(f"Skipping non-JSON SSE payload: {payload[:120]}")


def provider_error(provider: str, err: Any, fallback: str = "unknown error") -> str:
  """Render a provider error object into one message string."""
  if isinstance(err, dict):
    message = err.get("message") or fallback
    code = err.get("code") or err.get("type")
    return f"{provider} error ({code}): {message}" if code else f"{provider} error: {message}"
  if isinstance(err, str) and err:
    return f"{provider} error: {err}"
  return f"{provider} error: {fallback}"

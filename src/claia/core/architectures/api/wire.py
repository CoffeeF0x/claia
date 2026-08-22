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
from typing import Any, Dict, Iterator


logger = logging.getLogger(__name__)


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

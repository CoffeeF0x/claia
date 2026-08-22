"""
Tool-call payload decoder for the simple protocol.

The post-overhaul ``BaseProtocol.execute`` contract receives the raw
content string between a tag's open and close tokens. For the simple
protocol that string is JSON; this module turns it into a usable
``(parameters, name_hint)`` tuple.

Two payload shapes are accepted:

- **Flat** — ``{"key": "value", ...}``: parameters live at the top of
  the object; ``name_hint`` is ``None``.
- **Envelope** — ``{"name": "<qualified_name>", "parameters": {...}}``:
  parameters live under the ``parameters`` key; the ``name`` field is
  surfaced as ``name_hint`` for callers that want to cross-check it.

The dispatch target is always the ``qualified_name`` argument supplied
by the registry; ``name_hint`` is informational only.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple


def decode_payload(raw_payload: str) -> Tuple[Dict[str, Any], Optional[str]]:
  """Decode ``raw_payload`` into ``(parameters, name_hint)``.

  Returns ``({}, None)`` for empty or whitespace-only input. For an
  envelope-shaped object the function unwraps ``parameters`` and
  surfaces the ``name`` field as ``name_hint``; for a flat object it
  returns the object itself with ``name_hint=None``.

  Raises:
    ValueError: when the payload is non-empty but does not parse as
      JSON, or when the parsed value is not a JSON object.
  """
  text = (raw_payload or "").strip()
  if not text:
    return {}, None

  try:
    decoded = json.loads(text)
  except json.JSONDecodeError as exc:
    raise ValueError(f"failed to decode JSON payload: {exc}") from exc

  if not isinstance(decoded, dict):
    raise ValueError(
      f"JSON payload must decode to an object, got {type(decoded).__name__}"
    )

  parameters = decoded.get("parameters")
  if isinstance(parameters, dict):
    name_hint = decoded.get("name")
    return parameters, (name_hint if isinstance(name_hint, str) else None)

  return decoded, None


__all__ = ["decode_payload"]

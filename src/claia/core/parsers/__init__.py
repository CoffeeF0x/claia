"""
Streaming tag parser for assistant content.

The agent loop drives a ``StreamingTagParser`` per model turn. The
parser consumes streamed text chunks and yields a sequence of
``TextEvent``, ``TagEvent``, and ``ParseError`` items as they
become unambiguous. The resulting tag events are converted to
utility messages by the consumer; tool-typed events are dispatched
to the registry's tool index.

Public API:

- ``TagType`` — categorical kind of a parsed span (TOOL / THINKING /
  REFERENCE / …).
- ``TagSpec`` — concrete delimiter description for one tag type.
- ``TextEvent`` / ``TagEvent`` / ``ParseError`` — parser outputs.
- ``ParseEvent`` — union alias.
- ``StreamingTagParser`` — the parser itself.
- ``DEFAULT_TAGS`` — global default ``TagSpec`` per ``TagType``.
- ``resolve_tag_specs`` — merge ``DEFAULT_TAGS`` with per-model
  overrides into the list to feed into the parser.
"""

from .defaults import DEFAULT_TAGS
from .resolution import resolve_tag_specs
from .streaming import StreamingTagParser
from .types import (
  ParseError,
  ParseEvent,
  TagEvent,
  TagSpec,
  TagType,
  TextEvent,
)

__all__ = [
  "DEFAULT_TAGS",
  "ParseError",
  "ParseEvent",
  "StreamingTagParser",
  "TagEvent",
  "TagSpec",
  "TagType",
  "TextEvent",
  "resolve_tag_specs",
]

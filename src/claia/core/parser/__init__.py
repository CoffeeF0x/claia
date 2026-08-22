"""
Tag parser for assistant content.

The agent loop drives a ``TagParser`` per model turn. The parser consumes
streamed text chunks and yields a sequence of ``TextEvent``, ``TagEvent``,
and ``ParseError`` items as they become unambiguous. The resulting tag events
are converted to utility messages by the consumer; tool-typed events are
dispatched to the registry's tool index.

Public API:

- ``TagType`` — categorical kind of a parsed span (TOOL / THINKING /
  REFERENCE / …).
- ``TagSpec`` — concrete delimiter description for one tag type.
- ``TextEvent`` / ``TagEvent`` / ``ParseError`` — parser outputs.
- ``ParseEvent`` — union alias.
- ``TagParser`` — the parser itself.
- ``DEFAULT_TAGS`` — global default ``TagSpec`` per ``TagType``.
- ``resolve_tag_specs`` — merge ``DEFAULT_TAGS`` with per-model
  overrides into the list to feed into the parser.
"""

from .defaults import DEFAULT_TAGS
from .resolution import resolve_tag_specs
from .tag_parser import TagParser
from .types import (
  ParseError,
  ParseEvent,
  TagEvent,
  TagSpec,
  TextEvent,
)
from ..enums.parser import TagType

__all__ = [
  "DEFAULT_TAGS",
  "ParseError",
  "ParseEvent",
  "TagEvent",
  "TagParser",
  "TagSpec",
  "TagType",
  "TextEvent",
  "resolve_tag_specs",
]

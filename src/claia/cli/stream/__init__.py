"""
Display-side stream routing for the CLI.

Public names:

- ``StreamRouter`` — chunks/artifacts in, block events out.
- ``Channel`` / ``ToolSource`` — block-event enums.
- ``TextDelta`` / ``ToolCall`` / ``ArtifactNotice`` / ``StreamEnd`` —
  the block events themselves (``BlockEvent`` is the union alias).
"""

from .blocks import (
  ArtifactNotice,
  BlockEvent,
  Channel,
  StreamEnd,
  TextDelta,
  ToolCall,
  ToolSource,
)
from .router import StreamRouter

__all__ = [
  "ArtifactNotice",
  "BlockEvent",
  "Channel",
  "StreamEnd",
  "StreamRouter",
  "TextDelta",
  "ToolCall",
  "ToolSource",
]

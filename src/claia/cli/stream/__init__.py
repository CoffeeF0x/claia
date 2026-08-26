"""
Display-side stream routing for the CLI.

Public names:

- ``StreamRouter`` — chunks/artifacts in, block events out.
- ``replay_turn`` — persisted assistant turn in, block events out.
- ``Channel`` / ``ToolSource`` — block-event enums.
- ``TextDelta`` / ``ToolCall`` / ``ToolResult`` / ``ArtifactNotice``
  / ``StreamEnd`` — the block events themselves (``BlockEvent`` is
  the union alias).
"""

from .blocks import (
  ArtifactNotice,
  BlockEvent,
  Channel,
  StreamEnd,
  TextDelta,
  ToolCall,
  ToolResult,
  ToolSource,
)
from .replay import replay_turn
from .router import StreamRouter

__all__ = [
  "ArtifactNotice",
  "BlockEvent",
  "Channel",
  "StreamEnd",
  "StreamRouter",
  "TextDelta",
  "ToolCall",
  "ToolResult",
  "ToolSource",
  "replay_turn",
]

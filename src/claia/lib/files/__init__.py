"""
Init for CLAIA lib files package.

Provides convenient imports for file types and conversation-related classes.
"""

# File types
from .base import BaseFile
from .text import TextFile
from .image import ImageFile
from .prompt import Prompt
from .manifest import FileManifest

# Optional/placeholder: audio module may not define symbols yet
try:
  from .audio import AudioFile  # type: ignore
except Exception:
  # Safe to ignore if AudioFile is not yet implemented
  pass

# Re-export conversation package symbols for convenience
# from .conversation import (
#   Conversation,
#   Message,
#   Action,
#   ToolDefinition,
#   ConversationSettings,
# )

__all__ = [
  "BaseFile",
  "TextFile",
  "ImageFile",
  "Prompt",
  "FileManifest",
  "Conversation",
  "Message",
  "Action",
  "ToolDefinition",
  "ConversationSettings",
]

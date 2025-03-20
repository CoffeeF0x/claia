# External dependencies
from enum import Enum


########################################################################
#                                ENUMS                                 #
########################################################################
class MessageRole(Enum):
  """Roles for conversation messages."""
  SYSTEM    = "system"
  USER      = "user"
  ASSISTANT = "assistant"
  TOOL      = "tool"
  TOOL_CALL = "tool-call"
  FILE      = "file"
  IMAGE     = "image"
  AUDIO     = "audio"
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

class ActionType(Enum):
  """Action Types for conversations"""
  REQUEST = "request"
  RESPONSE = "response"
  UPDATE_SYSTEM_PROMPT = "update_system_prompt"
  PROCESS_MESSAGE = "process_message"
  ATTACH_FILE = "attach_file"
# External dependencies
from typing import Dict, Any, Optional, List
import logging
import json
import time
import uuid
import re

# Internal dependencies
from ...enums.conversation import MessageRole



########################################################################
#                              CONSTANTS                               #
########################################################################
LEFT_ARG_WRAPPER = "{"
RIGHT_ARG_WRAPPER = "}"



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               MESSAGE                                #
########################################################################
class Message:
  """
  Class representing a message in a conversation.

  Messages can contain inline arguments enclosed in wrapper characters
  (by default '{}'), which are extracted and stored separately from the content.

  Supported argument formats:
  - Key-value with equals: {key=value}
  - JSON-style with colon: {key: value}
  - CLI-style with double-dash: {--key value}
  - Flag-style (boolean): {key} or {--key}

  Examples:
    "Hello {model=gpt-4}" → content: "Hello", args: {"model": "gpt-4"}
    "Image {style: cartoon} {hd}" → content: "Image", args: {"style": "cartoon", "hd": true}
    "Translate {--lang spanish}" → content: "Translate", args: {"lang": "spanish"}
  """

  def __init__(self,
               speaker: MessageRole,
               content: str,
               message_id: Optional[str] = None,
               file_ids: Optional[List[str]] = None,
               created_at: Optional[float] = None,
               updated_at: Optional[float] = None,
               inline_args: Optional[Dict[str, Any]] = None,
               tool_pattern_name: Optional[str] = None,
               tool_protocol_name: Optional[str] = None):
    """
    Initialize a message.

    Args:
        speaker: The speaker of the message
        content: The content of the message
        message_id: Optional ID for the message (generated if not provided)
        file_ids: Optional list of file IDs attached to the message
        created_at: Optional timestamp for creation time
        updated_at: Optional timestamp for last update time
        inline_args: Optional arguments extracted from the message content
        tool_pattern_name: Optional name of the tool pattern used for this message
        tool_protocol_name: Optional name of the tool protocol used for this message
    """
    self.message_id = message_id or str(uuid.uuid4())
    self.speaker = speaker if isinstance(speaker, MessageRole) else MessageRole(speaker)
    self.content = content
    self.file_ids = file_ids or []
    self.created_at = created_at or time.time()
    self.updated_at = updated_at or self.created_at
    self.inline_args = inline_args or {}
    self.tool_pattern_name = tool_pattern_name
    self.tool_protocol_name = tool_protocol_name

  def to_dict(self) -> Dict[str, Any]:
    """Convert the message to a dictionary."""
    return {
      "message_id": self.message_id,
      "speaker": self.speaker.value,
      "content": self.content,
      "file_ids": self.file_ids,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
      "inline_args": self.inline_args,
      "tool_pattern_name": self.tool_pattern_name,
      "tool_protocol_name": self.tool_protocol_name
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'Message':
    """Create a message from a dictionary."""
    return cls(
      speaker=data.get("speaker", MessageRole.USER.value),
      content=data.get("content", ""),
      message_id=data.get("message_id"),
      file_ids=data.get("file_ids", []),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
      inline_args=data.get("inline_args", {}) or data.get("query_args", {}),  # Handle both old and new field names
      tool_pattern_name=data.get("tool_pattern_name"),
      tool_protocol_name=data.get("tool_protocol_name")
    )

  def extract_inline_args(self, left_wrapper: str = LEFT_ARG_WRAPPER, right_wrapper: str = RIGHT_ARG_WRAPPER) -> str:
    """
    Extract inline arguments from the message content and remove them from the content.

    Supports multiple argument formats:
    - Key-value with equals: {key=value}
    - JSON-style with colon: {key: value}
    - CLI-style with double-dash: {--key value}
    - Flag-style (boolean): {key} or {--key}

    Args:
        left_wrapper: The left wrapper character for arguments
        right_wrapper: The right wrapper character for arguments

    Returns:
        str: The content with arguments removed
    """
    # Start with the current content
    updated_content = self.content

    # Look for argument patterns like {key=value}, {key: value}, etc.
    arg_pattern = re.compile(f"\\{left_wrapper}([^{left_wrapper}{right_wrapper}]+?)\\{right_wrapper}")
    matches = arg_pattern.finditer(self.content)

    for match in matches:
      arg_text = match.group(1)
      full_match = match.group(0)

      # Parse the argument
      try:
        # Check for different argument formats

        # Format 1: Key-value with equals sign {key=value}
        if "=" in arg_text:
          key, value = arg_text.split("=", 1)
          key = key.strip()
          value = value.strip()

          # Try to convert value to appropriate type
          value = self._convert_value_type(value)
          self.inline_args[key] = value

        # Format 2: JSON-style with colon {key: value}
        elif ":" in arg_text:
          key, value = arg_text.split(":", 1)
          key = key.strip()
          value = value.strip()

          # Try to convert value to appropriate type
          value = self._convert_value_type(value)
          self.inline_args[key] = value

        # Format 3: CLI-style with double-dash {--key value}
        elif arg_text.startswith("--") and " " in arg_text:
          parts = arg_text.split(" ", 1)
          key = parts[0][2:].strip()  # Remove -- prefix
          value = parts[1].strip()

          if key and value:
            # Try to convert value to appropriate type
            value = self._convert_value_type(value)
            self.inline_args[key] = value

        # Format 4: CLI-style flag {--key}
        elif arg_text.startswith("--"):
          key = arg_text[2:].strip()  # Remove -- prefix
          if key:
            self.inline_args[key] = True

        # Format 5: Simple flag {key}
        else:
          key = arg_text.strip()
          if key:
            self.inline_args[key] = True

        # Remove the argument from the content
        updated_content = updated_content.replace(full_match, "", 1)

      except Exception as e:
        logger.warning(f"Failed to parse argument '{arg_text}': {e}")

    # Update the content and return it
    self.content = updated_content.strip()
    return self.content

  def _convert_value_type(self, value: str) -> Any:
    """
    Convert a string value to an appropriate type.

    Args:
        value: The string value to convert

    Returns:
        The converted value
    """
    # Boolean values
    if value.lower() == "true":
      return True
    elif value.lower() == "false":
      return False

    # Numbers
    elif value.isdigit():
      return int(value)
    elif re.match(r"^-?\d+(\.\d+)?$", value):
      return float(value)

    # Lists and dictionaries (JSON)
    elif (value.startswith("[") and value.endswith("]")) or (value.startswith("{") and value.endswith("}")):
      try:
        return json.loads(value)
      except json.JSONDecodeError:
        # If not valid JSON, return as string
        pass

    # Default: return as string
    return value

  def get_inline_args(self) -> Dict[str, Any]:
    """
    Get the extracted inline arguments from this message.

    Returns:
        Dict[str, Any]: Dictionary of extracted arguments
    """
    return self.inline_args.copy()

  def has_inline_args(self) -> bool:
    """
    Check if this message has any inline arguments.

    Returns:
        bool: True if message has inline arguments, False otherwise
    """
    return bool(self.inline_args)

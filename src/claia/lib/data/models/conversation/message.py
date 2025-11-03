"""
Message data model for conversations.

Messages represent individual turns in a conversation, with support for
inline arguments and thread-safe concurrent updates for streaming.
"""

# External dependencies
from typing import Dict, Any, Optional, List
import logging
import json
import time
import uuid
import re
import threading

# Internal dependencies
from ....enums.conversation import MessageRole


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
    
    Thread Safety:
        Messages include thread-safe methods for concurrent updates during streaming
        and tool processing. Use safe_* methods when multiple threads access the same message.
    """

    def __init__(self,
                 speaker: MessageRole,
                 content: str,
                 message_id: Optional[str] = None,
                 file_ids: Optional[List[str]] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None,
                 inline_args: Optional[Dict[str, Any]] = None):
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
        """
        self.message_id = message_id or str(uuid.uuid4())
        self.speaker = speaker if isinstance(speaker, MessageRole) else MessageRole(speaker)
        self.content = content
        self.file_ids = file_ids or []
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at
        self.inline_args = inline_args or {}
        
        # Thread safety for concurrent updates (streaming + tool processing)
        self._content_lock = threading.Lock()

    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        return {
            "message_id": self.message_id,
            "speaker": self.speaker.value,
            "content": self.content,
            "file_ids": self.file_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "inline_args": self.inline_args
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
            inline_args=data.get("inline_args", {}) or data.get("query_args", {})  # Handle both old and new field names
        )

    # Thread-safe methods for concurrent updates
    
    def safe_update_content(self, new_content: str) -> None:
        """
        Thread-safe content update.
        
        Use this when multiple threads might be updating the message concurrently.
        
        Args:
            new_content: The new content to set
        """
        with self._content_lock:
            self.content = new_content
            self.updated_at = time.time()

    def safe_append_content(self, chunk: str) -> None:
        """
        Thread-safe append for streaming.
        
        Use this when streaming content from an API and you need to append chunks.
        
        Args:
            chunk: The content chunk to append
        """
        with self._content_lock:
            self.content += chunk
            self.updated_at = time.time()

    def safe_replace_substring(self, start: int, end: int, replacement: str) -> bool:
        """
        Thread-safe substring replacement for tool calls.
        
        Use this when replacing tool calls with their results while streaming continues.
        
        Args:
            start: Start index (inclusive) of the substring to replace
            end: End index (exclusive) of the substring to replace
            replacement: The replacement string
            
        Returns:
            bool: True if replacement succeeded, False if indices were invalid
        """
        with self._content_lock:
            if 0 <= start < end <= len(self.content):
                self.content = self.content[:start] + replacement + self.content[end:]
                self.updated_at = time.time()
                return True
            return False

    def safe_get_content(self) -> str:
        """
        Thread-safe content read.
        
        Use this when reading content that might be concurrently modified.
        
        Returns:
            str: A copy of the current content
        """
        with self._content_lock:
            return self.content

    # Inline arguments extraction

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


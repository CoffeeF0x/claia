"""
This module contains the conversation file handling class for CLAIA.

The Conversation class provides functionality for managing text-based conversations,
including support for inline arguments that can be extracted from messages.
These arguments can be used to pass settings or parameters within the message text.

Example of inline arguments (multiple formats supported):
    "Summarize this document {model=gpt-4} {temperature=0.7}"       # Equals format
    "Generate an image {model: dall-e-3} {creative}"                # JSON-style format
    "Translate to French {--model gpt-4} {--format json}"           # CLI-style format
"""

# TODO:
# - Attach a file should just send the path or url along with whether or not
#   it's a reference (optional), then identify and call the correct object
#   to attach the file. If a file id is passed, then validate and identify the type
# - Consider redesign so that an external file load is not required (ie, stored fully
#   in memory except on saves and loads)
# - Update the function definition to match our commands structure
# - Remove the settings object from tool calls?
# - Make sure tools still work after load (ie, are the references stored correctly?)

# External dependencies
import json
import uuid
import time
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Union, List, Tuple
import re

# Internal dependencies
from .text import TextFile
from enums import FileSubdirectory, ActionType, MessageRole, TagType, TagStatus



########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_CONVERSATION_TITLE = "New Conversation"

# Default tool format placeholder
DEFAULT_TOOL_FORMAT = """
[TOOL_CALL]{
"name": "tool_name",
"parameters": {
  "param1": "value1",
  "param2": "value2"
}
}[/TOOL_CALL]
"""

# Argument wrapper constants
LEFT_ARG_WRAPPER = "{"
RIGHT_ARG_WRAPPER = "}"



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods
T = TypeVar('T', bound='Conversation')



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



########################################################################
#                          TOOL DEFINITION                             #
########################################################################
class ToolDefinition:
  """
  Class representing a tool definition in a conversation.
  """

  def __init__(self,
               name: str,
               description: str,
               parameters: Dict[str, Any],
               returns: Dict[str, Any] = None,
               tool_id: Optional[str] = None,
               created_at: Optional[float] = None,
               updated_at: Optional[float] = None):
    """
    Initialize a tool definition.

    Args:
        name: The name of the tool
        description: The description of the tool
        parameters: The parameters of the tool
        returns: The return value schema of the tool (default: {"type": "string"})
        tool_id: Optional ID for the tool (generated if not provided)
        created_at: Optional timestamp for creation time
        updated_at: Optional timestamp for last update time
    """
    self.tool_id = tool_id or str(uuid.uuid4())
    self.name = name
    self.description = description
    self.parameters = parameters
    self.returns = returns or {"type": "string"}
    self.created_at = created_at or time.time()
    self.updated_at = updated_at or self.created_at

  def to_dict(self) -> Dict[str, Any]:
    """Convert the tool definition to a dictionary."""
    return {
      "tool_id": self.tool_id,
      "name": self.name,
      "description": self.description,
      "parameters": self.parameters,
      "returns": self.returns,
      "created_at": self.created_at,
      "updated_at": self.updated_at
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'ToolDefinition':
    """Create a tool definition from a dictionary."""
    return cls(
      name=data.get("name", ""),
      description=data.get("description", ""),
      parameters=data.get("parameters", {}),
      returns=data.get("returns", {"type": "string"}),
      tool_id=data.get("tool_id"),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at")
    )



########################################################################
#                                ACTION                                #
########################################################################
class Action:
  """
  Class representing an action in a conversation history.
  """

  def __init__(self,
               action_type: ActionType,
               metadata: Optional[Dict[str, Any]] = None,
               action_id: Optional[str] = None,
               timestamp: Optional[float] = None):
    """
    Initialize an action.

    Args:
        action_type: The type of action
        metadata: Optional metadata for the action
        action_id: Optional ID for the action (generated if not provided)
        timestamp: Optional timestamp for the action
    """
    self.action_id = action_id or str(uuid.uuid4())
    self.action_type = action_type if isinstance(action_type, ActionType) else ActionType[action_type]
    self.metadata = metadata or {}
    self.timestamp = timestamp or time.time()

  def to_dict(self) -> Dict[str, Any]:
    """Convert the action to a dictionary."""
    return {
      "action_id": self.action_id,
      "action_type": self.action_type.name,
      "metadata": self.metadata,
      "timestamp": self.timestamp
    }

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> 'Action':
    """Create an action from a dictionary."""
    return cls(
      action_type=data.get("action_type", ActionType.CREATE_CONVERSATION.name),
      metadata=data.get("metadata", {}),
      action_id=data.get("action_id"),
      timestamp=data.get("timestamp")
    )



########################################################################
#                             CONVERSATION                             #
########################################################################
class Conversation(TextFile):
  """
  Class for handling conversation files with specialized functionality.

  Features:
  - Stores conversations in JSON format
  - Manages conversation actions and messages
  - Tracks message history and attachments
  - Handles tagged content processing (e.g., function calls)
  - Inherits text file functionality for content operations
  """

  def __init__(self, base_directory: str, registry=None, **kwargs):
    """
    Initialize a conversation file.

    Args:
        base_directory: Base directory for the file
        registry: Optional Registry object for direct command execution
        **kwargs: Additional arguments to pass to the parent class
            custom_tag_formats (Optional[Dict[TagType, Tuple[str, str]]]):
                Overrides for default tag formats. Key is TagType enum,
                value is a tuple of (opening_tag, closing_tag).
    """
    # Extract conversation-specific kwargs
    self.title = kwargs.pop("title", DEFAULT_CONVERSATION_TITLE)
    self.prompt = kwargs.pop("prompt", "")
    initial_messages = kwargs.pop("messages", [])
    initial_actions = kwargs.pop("actions", [])
    initial_tools = kwargs.pop("tool_definitions", [])
    self.custom_tag_formats = kwargs.pop("custom_tag_formats", {})

    # Store registry reference if provided
    self.registry = registry

    # Ensure the file has .json extension
    file_name = kwargs.get("file_name")
    if file_name and not file_name.endswith(".json"):
      kwargs["file_name"] = f"{file_name}.json"

    # Set the subdirectory override before calling the parent constructor
    self._override_subdirectory = FileSubdirectory.CONVERSATION.value

    # Initialize as TextFile but ensure mime_type is application/json
    kwargs["mime_type"] = "application/json"
    super().__init__(base_directory=base_directory, **kwargs)

    # Initialize messages, actions, and tool definitions
    self.messages = []
    self.actions = []
    self.tool_definitions = []

    # Load initial messages and actions if provided
    for message_data in initial_messages:
      if isinstance(message_data, Message):
        self.messages.append(message_data)
      else:
        self.messages.append(Message.from_dict(message_data))

    for action_data in initial_actions:
      if isinstance(action_data, Action):
        self.actions.append(action_data)
      else:
        self.actions.append(Action.from_dict(action_data))

    # Load initial tool definitions if provided
    for tool_data in initial_tools:
      if isinstance(tool_data, ToolDefinition):
        self.tool_definitions.append(tool_data)
      else:
        self.tool_definitions.append(ToolDefinition.from_dict(tool_data))

    # If no actions are provided, create an initial action
    if not self.actions:
      self.add_action(ActionType.CREATE_CONVERSATION, {
        "title": self.title,
        "prompt": self.prompt
      })

    # Add conversation-specific metadata
    self.metadata.update({
      "title": self.title,
      "message_count": len(self.messages),
      "tool_count": len(self.tool_definitions),
      "has_custom_tags": bool(self.custom_tag_formats)
    })

  def _update_metadata(self):
    """
    Update conversation metadata before it is saved.
    """
    # Call parent's hook first (to get text stats)
    super()._update_metadata()

    # Update metadata with conversation-specific info
    self.metadata.update({
      "title": self.title,
      "message_count": len(self.messages),
      "tool_count": len(self.tool_definitions),
      "has_custom_tags": bool(self.custom_tag_formats)
    })

  def _get_default_content(self) -> Optional[str]:
    """
    Provide default content when saving without content.

    Returns:
        str: JSON representation of the conversation
    """
    # Create conversation data structure for file content
    content_data = {
      "conversation_id": self.file_id,
      "title": self.title,
      "prompt": self.prompt,
      "messages": [m.to_dict() for m in self.messages],
      "actions": [a.to_dict() for a in self.actions],
      "tool_definitions": [t.to_dict() for t in self.tool_definitions],
      "custom_tag_formats": {
        k.name: v for k, v in self.custom_tag_formats.items()
      },
      "created_at": self.timestamp
    }

    return json.dumps(content_data, indent=2)

  def _get_tag_format(self, tag_type: TagType) -> tuple[str, str]:
    """
    Gets the opening and closing tags for a given TagType.

    Checks for custom formats first, then falls back to defaults.
    The default closing tag is derived from the opening tag (e.g., [TAG] -> [/TAG]).

    Args:
        tag_type: The TagType enum member.

    Returns:
        A tuple containing the (opening_tag, closing_tag).
    """
    if tag_type in self.custom_tag_formats:
      return self.custom_tag_formats[tag_type]
    else:
      # Default format: [TAG_NAME] and [/TAG_NAME]
      opening_tag = tag_type.value
      # Basic derivation for closing tag (assumes format like "[TAG]")
      if opening_tag.startswith('[') and opening_tag.endswith(']'):
        closing_tag = f"[/ {opening_tag[1:-1]}]" # e.g., [/FUNCTION_CALL]
      else:
        # Fallback if format is unexpected (though less likely with enums)
        closing_tag = f"/{opening_tag}"
      return opening_tag, closing_tag

  def _get_tag_type_from_closing_tag(self, closing_tag_str: str) -> Optional[TagType]:
      """Helper to determine the TagType associated with a closing tag string."""
      for tag_type in TagType:
          opening_tag, closing_tag = self._get_tag_format(tag_type)
          if closing_tag_str == closing_tag:
              return tag_type
      return None

  def find_tags(self, content: str) -> list[dict]:
    """
    Identifies and extracts tagged sections in content, handling nesting and malformed tags.

    Uses a stack-based approach to parse tags according to TagType enums and
    custom formats defined in the conversation.

    Args:
        content: The text content to process.

    Returns:
        A list of dictionaries, each representing a found tag attempt:
          {
            "type": TagType,          # The type of the *opening* tag
            "status": TagStatus,      # The status of this tag pairing
            "opening_tag": str,       # The opening tag string found
            "closing_tag": Optional[str], # The closing tag string found (if any)
            "content": Optional[str], # Raw content string inside the tags (if closed)
            "start_index": int,       # Start index of the opening tag
            "end_index": Optional[int]  # Index *after* the closing tag (if closed)
          }
        The list includes entries for successfully closed tags, mismatched closures,
        and unclosed tags. It's generally sorted by opening tag start index.
    """
    found_tags_details = []
    open_tags_stack = [] # Stack to keep track of open tags: {'type': TagType, 'start': int, 'opening_tag': str}

    # Generate regex patterns for all possible opening and closing tags
    all_tags_patterns = []
    tag_type_map = {} # Map tag string back to TagType enum
    for tag_type in TagType:
        opening, closing = self._get_tag_format(tag_type)
        all_tags_patterns.extend([re.escape(opening), re.escape(closing)])
        tag_type_map[opening] = {'type': tag_type, 'is_opening': True}
        tag_type_map[closing] = {'type': tag_type, 'is_opening': False}

    # Combine patterns into a single regex for efficient searching
    # This finds *any* potential tag marker
    combined_pattern = re.compile('|'.join(all_tags_patterns))

    last_index = 0
    for match in combined_pattern.finditer(content):
        tag_str = match.group(0)
        start, end = match.span()
        tag_info = tag_type_map.get(tag_str)

        if not tag_info: # Should not happen with how pattern is built, but safe check
            continue

        if tag_info['is_opening']:
            # Found an opening tag, push onto stack
            open_tags_stack.append({
                'type': tag_info['type'],
                'start': start,
                'opening_tag': tag_str
            })
        else:
            # Found a closing tag
            closing_tag_type = tag_info['type']
            closing_tag_str = tag_str

            if open_tags_stack:
                # There's an open tag waiting to be closed
                last_open_tag = open_tags_stack.pop()
                tag_content = content[last_open_tag['start'] + len(last_open_tag['opening_tag']) : start]

                status = TagStatus.CLOSED
                if last_open_tag['type'] != closing_tag_type:
                    status = TagStatus.CLOSED_MISMATCH
                    logger.warning(f"Tag mismatch: Opened with {last_open_tag['opening_tag']} "
                                   f"but closed with {closing_tag_str} at index {start}.")

                found_tags_details.append({
                    "type": last_open_tag['type'],
                    "status": status,
                    "opening_tag": last_open_tag['opening_tag'],
                    "closing_tag": closing_tag_str,
                    "content": tag_content,
                    "start_index": last_open_tag['start'],
                    "end_index": end
                })
            else:
                # Found a closing tag without a corresponding open tag on stack
                logger.warning(f"Found closing tag '{closing_tag_str}' at index {start} with no matching open tag.")
                # Optionally add a MALFORMED_UNOPENED entry here if needed
                # found_tags_details.append({
                #     "type": closing_tag_type, # Type of the closing tag found
                #     "status": TagStatus.MALFORMED_UNOPENED,
                #     "opening_tag": None,
                #     "closing_tag": closing_tag_str,
                #     "content": None,
                #     "start_index": None, # Or maybe 'start' of the closing tag?
                #     "end_index": end
                # })

        last_index = end # Keep track for unclosed tags at the end

    # Handle any tags left unclosed on the stack at the end of the content
    for unclosed_tag in open_tags_stack:
        found_tags_details.append({
            "type": unclosed_tag['type'],
            "status": TagStatus.MALFORMED_UNCLOSED,
            "opening_tag": unclosed_tag['opening_tag'],
            "closing_tag": None,
            "content": None, # Or content from start to end of string? Decide based on need.
            "start_index": unclosed_tag['start'],
            "end_index": None
        })

    # Sort the results primarily by start index for consistency
    found_tags_details.sort(key=lambda x: x['start_index'] if x['start_index'] is not None else float('inf'))

    return found_tags_details

  def process_tool_calls_in_content(self, content: str, settings=None) -> str:
    """
    Finds and executes tool calls within the content, replacing tags with results.

    Uses find_tags to locate potential tool calls, then parses, executes via the
    command registry, and replaces them in the content string.

    Args:
      content: The text content containing potential tool calls.
      settings: Optional settings object to pass to tool execution.

    Returns:
      The processed content string with tool call tags replaced by their results
      or error messages.
    """
    processed_content = content
    found_tags = self.find_tags(processed_content)

    for tag in reversed(found_tags):
      if tag['type'] == TagType.TOOL_CALL and tag['status'] == TagStatus.CLOSED:
        tool_name = "unknown"
        parameters = {} # Initialize parameters
        result_message = ""
        try:
          # Parse the JSON content inside the tag
          tool_call_data = json.loads(tag['content'])
          tool_name = tool_call_data.get("name", "unknown")
          parameters = tool_call_data.get("parameters", {})

          # Execute the tool function using registry
          if self.registry:
            # Convert parameters to command-line format for run method
            command_args = [tool_name]

            # Add all parameters as key=value pairs
            for key, value in parameters.items():
              # Handle different parameter types
              if isinstance(value, bool):
                if value:
                  # For boolean True, just add the flag
                  command_args.append(f"--{key}")
              elif value is not None:
                # For other types, use key=value format
                command_args.append(f"{key}={value}")

            # Execute the command using run method
            result = self.registry.run(command_args, settings)

            # Extract message from Result object
            if result.is_success() and result.get_message():
              result_message = result.get_message()
            elif result.is_error():
              result_message = f"[TOOL RESULT: (ERROR) {result.get_message()}]"
            elif result.is_exit():
              result_message = f"[TOOL RESULT: (EXIT) {result.get_message()}]"
            else:
              result_message = f"[TOOL RESULT: (UNKNOWN) {result.get_message()}]"
          else:
            result_message = f"[TOOL RESULT: (ERROR) No command registry available to execute tool '{tool_name}']"
            logger.error(f"No registry available to execute tool: {tool_name}")

          # Add action for successful processing
          self.add_action(ActionType.PROCESS_FUNCTION_CALL, {
              "tool_name": tool_name,
              "parameters": parameters,
              "result_preview": result_message[:100] + "..." if len(result_message) > 100 else result_message
          })

        except json.JSONDecodeError as e:
          logger.error(f"Failed to parse JSON for tool call: {e}\nContent: {tag['content']}")
          result_message = f"[ERROR: Invalid JSON in tool call - {e}]"
          self.add_action(ActionType.PROCESS_FUNCTION_CALL, {
              "tool_name": tool_name,
              "parameters": parameters,
              "error": "JSONDecodeError",
              "content_preview": tag['content'][:100] + "..."
          })
        except Exception as e:
          logger.error(f"Unexpected error processing tool call for '{tool_name}': {e}")
          result_message = f"[ERROR: Failed to process tool '{tool_name}' - {e}]"
          self.add_action(ActionType.PROCESS_FUNCTION_CALL, {
              "tool_name": tool_name,
              "parameters": parameters,
              "error": str(e),
              "content_preview": tag['content'][:100] + "..."
          })

        # Replace the original tag with the result/error
        if tag['start_index'] is not None and tag['end_index'] is not None:
            processed_content = processed_content[:tag['start_index']] + result_message + processed_content[tag['end_index']:]
        else:
            logger.error(f"Cannot replace tag for tool call '{tool_name}' due to missing indices.")

      elif tag['type'] == TagType.TOOL_CALL and tag['status'] != TagStatus.CLOSED:
         logger.warning(f"Skipping processing of non-closed/mismatched tool call tag ({tag['status'].name}) starting at {tag['start_index']}.")

    return processed_content

  def apply_substitutions(self, text: str, **kwargs) -> str:
    """
    Apply substitutions to the given text, replacing placeholders with values.

    This is the main method for all text substitutions in the conversation.
    Use this to process any text that contains placeholders, including:
    - Conversation prompts
    - Message content
    - Custom templates

    The substitution system handles:
    1. Simple placeholders like {name} or {date}
    2. Tool definition placeholders {tool_definitions}
    3. Tool format placeholders {tool_format}
    4. Any other placeholders passed via kwargs

    Examples:
        # Format a prompt
        formatted_prompt = conversation.apply_substitutions(conversation.prompt,
                                                          name="User",
                                                          topic="Python")

        # Process a message
        message = conversation.get_message(message_id)
        processed_message = conversation.apply_substitutions(message.content,
                                                           time="9:30 AM")

    Args:
        text: The text containing placeholders to replace
        **kwargs: Keyword arguments mapping placeholder names to values

    Returns:
        str: The text with all matched placeholders replaced
    """
    # Make a copy of the text to avoid modifying the original
    processed_text = text

    # Handle tool definitions placeholder
    if "{tool_definitions}" in processed_text and "tool_definitions" not in kwargs:
      # Use the stored tool definitions
      if self.tool_definitions:
        tool_defs_list = [
          {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
            "returns": t.returns
          }
          for t in self.tool_definitions
        ]
        kwargs["tool_definitions"] = json.dumps(tool_defs_list, indent=2)

    # Handle tool format placeholder
    if "{tool_format}" in processed_text and "tool_format" not in kwargs:
      kwargs["tool_format"] = DEFAULT_TOOL_FORMAT

    # Only attempt formatting if there are placeholders to replace
    if kwargs and any(f"{{{key}}}" in processed_text for key in kwargs):
      try:
        processed_text = processed_text.format(**kwargs)
      except KeyError as e:
        logger.warning(f"Missing key in text substitution: {e}")
      except Exception as e:
        logger.error(f"Error during text substitution: {e}")

    return processed_text

  def add_tool_definition(self, name: str, description: str, parameters: Dict[str, Any], returns: Dict[str, Any] = None) -> ToolDefinition:
    """
    Add a tool definition to the conversation.

    Args:
        name: The name of the tool
        description: The description of the tool
        parameters: The parameters of the tool
        returns: The return value schema of the tool (default: {"type": "string"})

    Returns:
        ToolDefinition: The created tool definition
    """
    # First check if a tool with the same name already exists
    for tool in self.tool_definitions:
      if tool.name == name:
        logger.warning(f"Tool with name '{name}' already exists. Use update_tool_definition instead.")
        return tool

    # Create a new tool definition
    tool_def = ToolDefinition(name=name, description=description, parameters=parameters, returns=returns)
    self.tool_definitions.append(tool_def)

    # Add an action for this tool addition
    self.add_action(ActionType.ADD_TOOL_DEFINITION, {
      "tool_id": tool_def.tool_id,
      "name": name,
      "description": description[:50] + "..." if len(description) > 50 else description
    })

    return tool_def

  def update_tool_definition(self, tool_id: str, name: Optional[str] = None,
                                description: Optional[str] = None,
                                parameters: Optional[Dict[str, Any]] = None,
                                returns: Optional[Dict[str, Any]] = None) -> Optional[ToolDefinition]:
    """
    Update a tool definition in the conversation.

    Args:
        tool_id: The ID of the tool to update
        name: Optional new name for the tool
        description: Optional new description for the tool
        parameters: Optional new parameters for the tool
        returns: Optional new return value schema for the tool

    Returns:
        Optional[ToolDefinition]: The updated tool definition, or None if not found
    """
    # Find the tool
    for i, tool in enumerate(self.tool_definitions):
      if tool.tool_id == tool_id:
        # Update tool properties if provided
        old_name = tool.name
        old_description = tool.description

        if name is not None:
          tool.name = name
        if description is not None:
          tool.description = description
        if parameters is not None:
          tool.parameters = parameters
        if returns is not None:
          tool.returns = returns

        # Update timestamp
        tool.updated_at = time.time()

        # Add an action for this update
        self.add_action(ActionType.UPDATE_TOOL_DEFINITION, {
          "tool_id": tool_id,
          "old_name": old_name,
          "new_name": tool.name,
          "description": tool.description[:50] + "..." if len(tool.description) > 50 else tool.description
        })

        return tool

    logger.error(f"Tool definition not found for update: {tool_id}")
    return None

  def remove_tool_definition(self, tool_id: str) -> bool:
    """
    Remove a tool definition from the conversation.

    Args:
        tool_id: The ID of the tool to remove

    Returns:
        bool: True if the tool was removed, False otherwise
    """
    # Find the tool
    for i, tool in enumerate(self.tool_definitions):
      if tool.tool_id == tool_id:
        # Remove the tool
        removed_tool = self.tool_definitions.pop(i)

        # Add an action for this removal
        self.add_action(ActionType.REMOVE_TOOL_DEFINITION, {
          "tool_id": tool_id,
          "name": removed_tool.name
        })

        return True

    logger.error(f"Tool definition not found for removal: {tool_id}")
    return False

  def get_tool_definition(self, tool_id: str) -> Optional[ToolDefinition]:
    """
    Get a tool definition by ID.

    Args:
        tool_id: The ID of the tool to get

    Returns:
        Optional[ToolDefinition]: The tool definition, or None if not found
    """
    for tool in self.tool_definitions:
      if tool.tool_id == tool_id:
        return tool
    return None

  def get_tool_definition_by_name(self, name: str) -> Optional[ToolDefinition]:
    """
    Get a tool definition by name.

    Args:
        name: The name of the tool to get

    Returns:
        Optional[ToolDefinition]: The tool definition, or None if not found
    """
    for tool in self.tool_definitions:
      if tool.name == name:
        return tool
    return None

  def add_message(self, speaker: Union[MessageRole, str], content: str, file_ids: Optional[List[str]] = None) -> Message:
    """
    Add a message to the conversation.

    Args:
        speaker: The speaker of the message
        content: The content of the message
        file_ids: Optional list of file IDs attached to the message

    Returns:
        Message: The created message
    """
    # Create a new message
    message = Message(speaker=speaker, content=content, file_ids=file_ids or [])

    # Extract arguments from the message content
    message.extract_inline_args()

    self.messages.append(message)

    # Add an action for this message
    action_metadata = {
      "message_id": message.message_id,
      "speaker": message.speaker.value,
      "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
    }

    # Add query args to metadata if present
    if message.has_inline_args():
      action_metadata["has_inline_args"] = True
      action_metadata["inline_args_count"] = len(message.inline_args)

    self.add_action(ActionType.CREATE_MESSAGE, action_metadata)

    return message

  def update_message(self, message_id: str, content: Optional[str] = None, file_ids: Optional[List[str]] = None) -> Optional[Message]:
    """
    Update a message in the conversation.

    Args:
        message_id: The ID of the message to update
        content: Optional new content for the message
        file_ids: Optional new list of file IDs

    Returns:
        Optional[Message]: The updated message, or None if not found
    """
    # Find the message
    for i, message in enumerate(self.messages):
      if message.message_id == message_id:
        # Track if query args were changed
        had_inline_args_before = message.has_inline_args()
        old_inline_args_count = len(message.inline_args) if had_inline_args_before else 0

        # Update message properties if provided
        if content is not None:
          message.content = content
          # Reset inline_args before re-extracting
          message.inline_args = {}
          message.extract_inline_args()

        if file_ids is not None:
          message.file_ids = file_ids

        # Update timestamp
        message.updated_at = time.time()

        # Prepare action metadata
        action_metadata = {
          "message_id": message_id,
          "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
        }

        # Add query args info to metadata if changed
        if content is not None:
          action_metadata["inline_args_changed"] = had_inline_args_before != message.has_inline_args() or old_inline_args_count != len(message.inline_args)
          if message.has_inline_args():
            action_metadata["has_inline_args"] = True
            action_metadata["inline_args_count"] = len(message.inline_args)

        # Add an action for this update
        self.add_action(ActionType.UPDATE_MESSAGE, action_metadata)

        return message

    logger.error(f"Message not found for update: {message_id}")
    return None

  def delete_message(self, message_id: str) -> bool:
    """
    Delete a message from the conversation.

    Args:
        message_id: The ID of the message to delete

    Returns:
        bool: True if the message was deleted, False otherwise
    """
    # Find the message
    for i, message in enumerate(self.messages):
      if message.message_id == message_id:
        # Remove the message
        deleted_message = self.messages.pop(i)

        # Add an action for this deletion
        self.add_action(ActionType.DELETE_MESSAGE, {
          "message_id": message_id,
          "speaker": deleted_message.speaker.value
        })

        return True

    logger.error(f"Message not found for deletion: {message_id}")
    return False

  def add_action(self, action_type: ActionType, metadata: Optional[Dict[str, Any]] = None) -> Action:
    """
    Add an action to the conversation history.

    Args:
        action_type: The type of action
        metadata: Optional metadata for the action

    Returns:
        Action: The created action
    """
    # Create a new action
    action = Action(action_type=action_type, metadata=metadata or {})
    self.actions.append(action)
    return action

  def get_message(self, message_id: str) -> Optional[Message]:
    """
    Get a message by ID.

    Args:
        message_id: The ID of the message to get

    Returns:
        Optional[Message]: The message, or None if not found
    """
    for message in self.messages:
      if message.message_id == message_id:
        return message
    return None

  def get_latest_message(self) -> Optional[Message]:
    """
    Get the latest message in the conversation.
    """
    return self.messages[-1] if self.messages else None

  def get_messages(self, speaker: Optional[Union[MessageRole, List[MessageRole]]] = None) -> List[Message]:
    """
    Get all messages, optionally filtered by speaker(s).

    Examples:
        # Get all messages
        all_messages = conversation.get_messages()

        # Get messages from a single speaker
        user_messages = conversation.get_messages(MessageRole.USER)

        # Get messages from multiple speakers
        dialogue = conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT])

        # Using string values (automatically converted to MessageRole)
        system_messages = conversation.get_messages("SYSTEM")

    Args:
        speaker: Optional speaker or list of speakers to filter by

    Returns:
        List[Message]: List of matching messages
    """
    if speaker is None:
      return self.messages

    # Convert single speaker to list for uniform handling
    speakers = [speaker] if not isinstance(speaker, list) else speaker

    # Convert any string values to MessageRole enums
    speakers = [s if isinstance(s, MessageRole) else MessageRole(s) for s in speakers]

    return [m for m in self.messages if m.speaker in speakers]

  def change_title(self, new_title: str) -> None:
    """
    Change the conversation title.

    Args:
        new_title: The new title for the conversation
    """
    old_title = self.title
    self.title = new_title

    # Add an action for this title change
    self.add_action(ActionType.CHANGE_TITLE, {
      "old_title": old_title,
      "new_title": new_title
    })

  def change_prompt(self, new_prompt: str) -> None:
    """
    Change the conversation prompt.

    Args:
        new_prompt: The new prompt for the conversation
    """
    old_prompt = self.prompt
    self.prompt = new_prompt

    # Add an action for this prompt change
    self.add_action(ActionType.CHANGE_PROMPT, {
      "old_prompt": old_prompt,
      "new_prompt": new_prompt
    })
    # self.add_action(ActionType.CHANGE_PROMPT, {
    #   "old_prompt": old_prompt[:50] + "..." if len(old_prompt) > 50 else old_prompt,
    #   "new_prompt": new_prompt[:50] + "..." if len(new_prompt) > 50 else new_prompt
    # })

  def attach_file(self, message_id: str, file_id: str) -> bool:
    """
    Attach a file to a message.

    Args:
        message_id: The ID of the message to attach to
        file_id: The ID of the file to attach

    Returns:
        bool: True if the file was attached, False otherwise
    """
    message = self.get_message(message_id)
    if not message:
      logger.error(f"Cannot attach file: message not found: {message_id}")
      return False

    if file_id in message.file_ids:
      logger.warning(f"File already attached to message: {file_id}")
      return True

    message.file_ids.append(file_id)
    message.updated_at = time.time()

    # Add an action for this file attachment
    self.add_action(ActionType.ATTACH_FILE, {
      "message_id": message_id,
      "file_id": file_id
    })

    return True

  def detach_file(self, message_id: str, file_id: str) -> bool:
    """
    Detach a file from a message.

    Args:
        message_id: The ID of the message to detach from
        file_id: The ID of the file to detach

    Returns:
        bool: True if the file was detached, False otherwise
    """
    message = self.get_message(message_id)
    if not message:
      logger.error(f"Cannot detach file: message not found: {message_id}")
      return False

    if file_id not in message.file_ids:
      logger.warning(f"File not attached to message: {file_id}")
      return False

    message.file_ids.remove(file_id)
    message.updated_at = time.time()

    # Add an action for this file detachment
    self.add_action(ActionType.DETACH_FILE, {
      "message_id": message_id,
      "file_id": file_id
    })

    return True

  @classmethod
  def create_conversation(cls: Type[T], base_directory: str, title: Optional[str] = None,
                        prompt: Optional[str] = None, registry=None, **kwargs) -> Optional[T]:
    """
    Create a new conversation file.

    Args:
        base_directory: Base directory for the file
        title: Optional title for the conversation
        prompt: Optional prompt for the conversation
        registry: Optional Registry object for direct command execution
        **kwargs: Additional arguments to pass to the constructor

    Returns:
        Optional[T]: A new Conversation instance, or None if creation failed
    """
    # Use default title if none provided
    title = title or DEFAULT_CONVERSATION_TITLE

    # Use default filename based on title if none provided
    if "file_name" not in kwargs:
      # Convert title to filename-friendly format
      filename = title.lower().replace(' ', '-')
      # Remove any non-alphanumeric characters except hyphens
      filename = ''.join(c for c in filename if c.isalnum() or c == '-')
      kwargs["file_name"] = f"{filename}.json"

    # Create the conversation instance
    conversation = cls(
      base_directory=base_directory,
      title=title,
      prompt=prompt or "",
      registry=registry,
      **kwargs
    )

    # Save the conversation to disk
    if conversation.save() is None:
      logger.error(f"Failed to save conversation: {title}")
      return None

    return conversation

  @classmethod
  def load_conversation(cls: Type[T], conversation_id: str, base_directory: str, registry=None) -> Optional[T]:
    """
    Load a conversation by ID.

    Args:
        conversation_id: The ID of the conversation to load
        base_directory: Base directory for file operations
        registry: Optional Registry object for direct command execution

    Returns:
        Optional[T]: The loaded conversation, or None if loading failed
    """
    # Try to load the conversation file
    result = cls.load(conversation_id, base_directory, load_content=True)
    if result and "content" in result:
      try:
        # Parse the JSON content
        data = json.loads(result["content"])

        # Extract valid constructor parameters from metadata
        metadata = result["metadata"].get("metadata", {})

        # Load custom tag formats from file data
        custom_formats_data = data.get("custom_tag_formats", {})
        custom_tag_formats = {}
        for name, fmt_tuple in custom_formats_data.items():
            try:
                tag_type_enum = TagType[name]
                if isinstance(fmt_tuple, list) and len(fmt_tuple) == 2:
                     custom_tag_formats[tag_type_enum] = tuple(fmt_tuple)
                else:
                    logger.warning(f"Invalid format for custom tag '{name}' in conversation {conversation_id}. Expected list of 2 strings.")
            except KeyError:
                logger.warning(f"Unknown TagType '{name}' found in custom tags for conversation {conversation_id}. Skipping.")

        # Create a new Conversation instance with the loaded data
        conversation = cls(
          base_directory=base_directory,
          file_id=result["metadata"].get("file_id"),
          file_name=result["metadata"].get("file_name"),
          mime_type=result["metadata"].get("mime_type"),
          timestamp=result["metadata"].get("timestamp"),
          title=data.get("title", DEFAULT_CONVERSATION_TITLE),
          prompt=data.get("prompt", ""),
          messages=[Message.from_dict(m) for m in data.get("messages", [])],
          actions=[Action.from_dict(a) for a in data.get("actions", [])],
          tool_definitions=[ToolDefinition.from_dict(t) for t in data.get("tool_definitions", [])],
          custom_tag_formats=custom_tag_formats,
          registry=registry,
          metadata=metadata
        )

        return conversation
      except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON from conversation file: {conversation_id}")
        return None

    logger.error(f"Conversation not found: {conversation_id}")
    return None

  @classmethod
  def list_conversations(cls: Type[T], base_directory: str) -> List[Dict[str, Any]]:
    """
    List all conversations in the base directory.

    Args:
        base_directory: Base directory for file operations

    Returns:
        List[Dict[str, Any]]: List of conversation metadata
    """
    # Find all conversation files
    conversations = cls.find_files_by_criteria(
      base_directory=base_directory,
      subdirectory=FileSubdirectory.CONVERSATION.value
    )

    # Extract metadata
    return [metadata for _, metadata in conversations.items()]

  def load_tool_definitions_from_list(self, tool_definitions: List[Dict[str, Any]]) -> List[ToolDefinition]:
    """
    Load tool definitions from a list of dictionaries.

    This is a helper method to add multiple tool definitions at once. It's useful when
    migrating from the old method of setting tool definitions as an attribute.

    Args:
        tool_definitions: List of tool definition dictionaries

    Returns:
        List[ToolDefinition]: List of created tool definitions
    """
    result = []
    for tool_def in tool_definitions:
      # Extract required fields
      name = tool_def.get("name")
      description = tool_def.get("description", "")
      parameters = tool_def.get("parameters", {})

      if not name:
        logger.warning("Skipping tool definition without a name")
        continue

      # Add the tool definition
      tool = self.add_tool_definition(name, description, parameters)
      result.append(tool)

    return result

  def get_all_tool_definitions(self) -> List[ToolDefinition]:
    """
    Get all tool definitions in the conversation.

    Returns:
        List[ToolDefinition]: List of all tool definitions
    """
    return self.tool_definitions

  def stream_message(self, message_id: str, content: str) -> Optional[Message]:
    """
    Update a message's content without adding an action to the history.

    This method is designed for streaming scenarios where a message is updated
    incrementally, and we don't want to create numerous update actions.
    Use this during streaming, then call update_message once streaming is complete.

    On the first call for a given message_id, a START_STREAM action will be added
    to indicate streaming has begun.

    Args:
        message_id: The ID of the message to update
        content: New content for the message

    Returns:
        Optional[Message]: The updated message, or None if not found
    """
    # Find the message
    for message in self.messages:
      if message.message_id == message_id:
        # Update message content without extracting inline args
        message.content = content

        # Update timestamp
        message.updated_at = time.time()

        # Check if we already have a START_STREAM action for this message
        has_start_stream_action = False
        for action in self.actions:
          if (action.action_type == ActionType.START_STREAM and
              action.metadata.get("message_id") == message_id):
            has_start_stream_action = True
            break

        # Add a START_STREAM action if this is the first streaming update
        if not has_start_stream_action:
          self.add_action(ActionType.START_STREAM, {
            "message_id": message_id,
            "speaker": message.speaker.value,
            "content_preview": content[:50] + "..." if len(content) > 50 else content
          })

        return message

    logger.error(f"Message not found for streaming update: {message_id}")
    return None

  def get_tool_definitions_as_list(self) -> List[Dict[str, Any]]:
    """
    Get all tool definitions as a list of dictionaries.

    This is useful for compatibility with systems expecting the old format.

    Returns:
        List[Dict[str, Any]]: List of tool definitions as dictionaries
    """
    return [
      {
        "name": t.name,
        "description": t.description,
        "parameters": t.parameters,
        "returns": t.returns
      }
      for t in self.tool_definitions
    ]

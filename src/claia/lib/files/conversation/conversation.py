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

# External dependencies
from typing import Dict, Any, Optional, Type, TypeVar, Union, List
import logging
import json
import time
import re

# Internal dependencies
from ..text import TextFile
from ...enums.conversation import ActionType, MessageRole, TagType, TagStatus
from ...enums.file import FileSubdirectory
from .tool_definition import ToolDefinition
from .action import Action
from .message import Message
from .conversation_settings import ConversationSettings



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



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)

# Type variable for class methods
T = TypeVar('T', bound='Conversation')



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

  def __init__(self, base_directory: str, **kwargs):
    """
    Initialize a conversation file.

    Args:
        base_directory: Base directory for the file
        **kwargs: Additional arguments to pass to the parent class
            custom_tag_formats (Optional[Dict[TagType, Tuple[str, str]]]):
                Overrides for default tag formats. Key is TagType enum,
                value is a tuple of (opening_tag, closing_tag).
    """
    # Extract conversation-specific kwargs
    self.title = kwargs.pop("title", DEFAULT_CONVERSATION_TITLE)
    self.prompt = kwargs.pop("prompt", "")
    self.tool_calling_prompt = kwargs.pop("tool_calling_prompt", None)
    self.tool_pattern_name = kwargs.pop("tool_pattern_name", None)
    self.tool_protocol_name = kwargs.pop("tool_protocol_name", None)
    initial_messages = kwargs.pop("messages", [])
    initial_actions = kwargs.pop("actions", [])
    initial_tools = kwargs.pop("tool_definitions", [])
    self.custom_tag_formats = kwargs.pop("custom_tag_formats", {})

    # Ensure the file has .json extension
    file_name = kwargs.get("file_name")
    if file_name and not file_name.endswith(".json"):
      kwargs["file_name"] = f"{file_name}.json"

    # Set the subdirectory override before calling the parent constructor
    self._override_subdirectory = FileSubdirectory.CONVERSATION.value

    # Initialize as TextFile but ensure mime_type is application/json
    kwargs["mime_type"] = "application/json"
    super().__init__(base_directory=base_directory, **kwargs)

    # Initialize messages, actions, tool definitions, and settings
    self.messages = []
    self.actions = []
    self.tool_definitions = []
    self.settings = kwargs.pop("settings", ConversationSettings())

    # Convert settings to ConversationSettings if necessary
    if not isinstance(self.settings, ConversationSettings):
      self.settings = ConversationSettings.from_dict(self.settings)

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
        "system_prompt": self.prompt,
        "tool_prompt": self.tool_calling_prompt
      })

    # Add conversation-specific metadata
    self.metadata.update({
      "title": self.title,
      "message_count": len(self.messages),
      "tool_count": len(self.tool_definitions),
      "has_custom_tags": bool(self.custom_tag_formats),
      "tool_calling_prompt": self.tool_calling_prompt,
      "tool_pattern_name": self.tool_pattern_name,
      "tool_protocol_name": self.tool_protocol_name,
      "settings": self.settings.to_dict()
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
      "has_custom_tags": bool(self.custom_tag_formats),
      "tool_calling_prompt": self.tool_calling_prompt,
      "tool_pattern_name": self.tool_pattern_name,
      "tool_protocol_name": self.tool_protocol_name,
      "settings": self.settings.to_dict()
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
      "tool_calling_prompt": self.tool_calling_prompt,
      "tool_pattern_name": self.tool_pattern_name,
      "tool_protocol_name": self.tool_protocol_name,
      "messages": [m.to_dict() for m in self.messages],
      "actions": [a.to_dict() for a in self.actions],
      "tool_definitions": [t.to_dict() for t in self.tool_definitions],
      "custom_tag_formats": {
        k.name: v for k, v in self.custom_tag_formats.items()
      },
      "settings": self.settings.to_dict(),
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
        closing_tag = f"[/{opening_tag[1:-1]}]" # e.g., [/FUNCTION_CALL]
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

  def set_tool_calling_prompt(self, prompt: str) -> None:
    """
    Set the tool calling prompt for this conversation.

    Args:
        prompt: The prompt used for tool calling detection/execution
    """
    old_prompt = self.tool_calling_prompt
    self.tool_calling_prompt = prompt

    # Add action to track this change (tool prompt specific)
    self.add_action(ActionType.CHANGE_TOOL_PROMPT, {
      "old_prompt": old_prompt,
      "new_prompt": prompt
    })

  def set_tool_pattern_name(self, pattern_name: str) -> None:
    """
    Set the tool pattern name for this conversation.

    Args:
        pattern_name: Name of the tool pattern extension to use
    """
    old_pattern = self.tool_pattern_name
    self.tool_pattern_name = pattern_name

    # Add action to track this change
    self.add_action(ActionType.UPDATE_SETTINGS, {
      "field": "tool_pattern_name",
      "old_value": old_pattern,
      "new_value": pattern_name
    })

  def set_tool_protocol_name(self, protocol_name: str) -> None:
    """
    Set the tool protocol name for this conversation.

    Args:
        protocol_name: Name of the tool protocol extension to use
    """
    old_protocol = self.tool_protocol_name
    self.tool_protocol_name = protocol_name

    # Add action to track this change
    self.add_action(ActionType.UPDATE_SETTINGS, {
      "field": "tool_protocol_name",
      "old_value": old_protocol,
      "new_value": protocol_name
    })

  def get_tool_calling_context(self) -> Dict[str, Any]:
    """
    Get the tool calling context for this conversation.

    Returns:
        Dict containing tool calling prompt, pattern name, and protocol name
    """
    return {
      "tool_calling_prompt": self.tool_calling_prompt,
      "tool_pattern_name": self.tool_pattern_name,
      "tool_protocol_name": self.tool_protocol_name,
      "tool_definitions": self.get_tool_definitions_as_list()
    }

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

  def get_system_prompt(self, include_tools: bool = True, **kwargs) -> Optional[str]:
    """
    Build the effective system prompt to send to models.

    - Starts with the conversation's base `prompt`.
    - Optionally appends `tool_calling_prompt` when include_tools is True.
    - Expands placeholders via `apply_substitutions()` so {tool_definitions} and
      {tool_format} are populated using the conversation's state.

    Args:
      include_tools: Whether to include tool-calling instructions.
      **kwargs: Optional substitution values for placeholders.

    Returns:
      The combined and substituted system prompt, or None if empty.
    """
    parts: List[str] = []
    if self.prompt:
      parts.append(self.prompt)
    if include_tools and self.tool_calling_prompt:
      parts.append(self.tool_calling_prompt)

    if not parts:
      return None

    combined = "\n\n".join(p.strip() for p in parts if p and p.strip())
    if not combined:
      return None

    return self.apply_substitutions(combined, **kwargs)

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

  def add_message(self, speaker: Union[MessageRole, str], content: str, file_ids: Optional[List[str]] = None,
                 tool_pattern_name: Optional[str] = None, tool_protocol_name: Optional[str] = None) -> Message:
    """
    Add a message to the conversation.

    Args:
        speaker: The speaker of the message
        content: The content of the message
        file_ids: Optional list of file IDs attached to the message
        tool_pattern_name: Optional name of the tool pattern used for this message
        tool_protocol_name: Optional name of the tool protocol used for this message

    Returns:
        Message: The created message
    """
    # Use conversation defaults if not specified, but keep None if both are None
    pattern_name = tool_pattern_name if tool_pattern_name is not None else self.tool_pattern_name
    protocol_name = tool_protocol_name if tool_protocol_name is not None else self.tool_protocol_name

    # Create a new message
    message = Message(
      speaker=speaker,
      content=content,
      file_ids=file_ids or [],
      tool_pattern_name=pattern_name,
      tool_protocol_name=protocol_name
    )

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

    # Add an action for this system prompt change
    self.add_action(ActionType.CHANGE_SYSTEM_PROMPT, {
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
                        prompt: Optional[str] = None, **kwargs) -> Optional[T]:
    """
    Create a new conversation file.

    Args:
        base_directory: Base directory for the file
        title: Optional title for the conversation
        prompt: Optional prompt for the conversation
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
      **kwargs
    )

    # Save the conversation to disk
    if conversation.save() is None:
      logger.error(f"Failed to save conversation: {title}")
      return None

    return conversation

  @classmethod
  def load_conversation(cls: Type[T], conversation_id: str, base_directory: str) -> Optional[T]:
    """
    Load a conversation by ID.

    Args:
        conversation_id: The ID of the conversation to load
        base_directory: Base directory for file operations

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
          tool_calling_prompt=data.get("tool_calling_prompt"),
          tool_pattern_name=data.get("tool_pattern_name"),
          tool_protocol_name=data.get("tool_protocol_name"),
          messages=[Message.from_dict(m) for m in data.get("messages", [])],
          actions=[Action.from_dict(a) for a in data.get("actions", [])],
          tool_definitions=[ToolDefinition.from_dict(t) for t in data.get("tool_definitions", [])],
          custom_tag_formats=custom_tag_formats,
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

  def replace_tool_call(self, message_id: str, start: int, end: int, replacement: str) -> bool:
    """
    Replace a tool call span within a message by string indices.

    On success, logs ActionType.REPLACE_TOOL_CALL and updates the message content.
    On failure (message missing, invalid indices), logs ActionType.FAILED_TOOL_CALL.

    Args:
      message_id: The ID of the message containing the tool call
      start: Start index (inclusive) of the span in the message content
      end: End index (exclusive) of the span in the message content
      replacement: The text to replace the span with

    Returns:
      bool: True on successful replacement; False otherwise
    """
    message = self.get_message(message_id)
    if not message:
      self.add_action(ActionType.FAILED_TOOL_CALL, {
        "message_id": message_id,
        "start": start,
        "end": end,
        "error": "message_not_found"
      })
      logger.error(f"replace_tool_call failed: message not found: {message_id}")
      return False

    content_len = len(message.content or "")
    if start < 0 or end < 0 or start >= end or end > content_len:
      self.add_action(ActionType.FAILED_TOOL_CALL, {
        "message_id": message_id,
        "start": start,
        "end": end,
        "error": "index_out_of_range"
      })
      logger.error(
        f"replace_tool_call failed: invalid indices start={start}, end={end}, len={content_len}"
      )
      return False

    new_content = (message.content[:start] if message.content else "") + replacement + (message.content[end:] if message.content else "")

    # Log successful replacement before content update for audit trace
    self.add_action(ActionType.REPLACE_TOOL_CALL, {
      "message_id": message_id,
      "start": start,
      "end": end,
      "replacement_preview": (replacement[:100] + "...") if len(replacement) > 100 else replacement
    })

    # Persist the content change (also records UPDATE_MESSAGE)
    self.update_message(message_id, content=new_content)
    return True

  def get_tool_calls(self, message_id: str, start_token: str, end_token: str) -> List[Dict[str, Any]]:
    """
    Find tool call spans in a message delimited by the given start/end tokens.

    Tokens are matched literally and non-overlapping, scanning left-to-right.

    Args:
      message_id: The ID of the message to inspect
      start_token: The literal start token (e.g., "[TOOL_CALL]")
      end_token: The literal end token (e.g., "[/TOOL_CALL]")

    Returns:
      List[Dict]: Each dict contains:
        {
          "start_index": int,    # index of the start token
          "end_index": int,      # index after the end token
          "content": str,        # text between the tokens
          "full_text": str       # text including the tokens
        }
    """
    message = self.get_message(message_id)
    if not message or message.content is None:
      return []

    text = message.content
    results: List[Dict[str, Any]] = []
    search_pos = 0

    while True:
      s = text.find(start_token, search_pos)
      if s == -1:
        break
      e = text.find(end_token, s + len(start_token))
      if e == -1:
        # No closing token; stop scanning to avoid infinite loop
        break

      end_idx = e + len(end_token)
      inner = text[s + len(start_token): e]
      full = text[s: end_idx]
      results.append({
        "start_index": s,
        "end_index": end_idx,
        "content": inner,
        "full_text": full
      })

      search_pos = end_idx

    return results

  def register_failed_tool_call(self, message_id: str, start: Optional[int], end: Optional[int], error: Optional[str] = None) -> None:
    """
    Register that a tool call within text failed, by string index range.

    Args:
      message_id: The ID of the message containing the tool call
      start: Optional start index (inclusive) of the tool call in the message content
      end: Optional end index (exclusive) of the tool call in the message content
      error: Optional error message or reason for failure
    """
    metadata = {
      "message_id": message_id,
      "start": start,
      "end": end
    }
    if error:
      metadata["error"] = error
    self.add_action(ActionType.FAILED_TOOL_CALL, metadata)

  def stream_message(self, message_id: str, content: str, append: bool = False, end: bool = False) -> Optional[Message]:
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
        append: If True, append the content to the existing message; if False, replace it

    Returns:
        Optional[Message]: The updated message, or None if not found
    """
    # Find the message
    for message in self.messages:
      if message.message_id == message_id:
        # Update message content without extracting inline args
        if append:
          message.content += content
        else:
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
            "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
          })

        if end:
          self.add_action(ActionType.END_STREAM, {
            "message_id": message_id,
            "speaker": message.speaker.value,
            "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
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

  def update_settings(self, settings: ConversationSettings) -> None:
    """
    Update conversation settings and record the action.

    Args:
        settings: A ConversationSettings object with the new settings
    """
    # Track what was changed for the action metadata
    changes = {}

    # Check if streaming setting changed
    if settings.streaming != self.settings.streaming:
      self.settings.streaming = settings.streaming
      changes["streaming"] = settings.streaming

    # Update text settings
    for key, value in settings.text_settings.items():
      if key not in self.settings.text_settings or self.settings.text_settings[key] != value:
        self.settings.text_settings[key] = value
        if "text_settings" not in changes:
          changes["text_settings"] = {}
        changes["text_settings"][key] = value

    # Update image settings
    for key, value in settings.image_settings.items():
      if key not in self.settings.image_settings or self.settings.image_settings[key] != value:
        self.settings.image_settings[key] = value
        if "image_settings" not in changes:
          changes["image_settings"] = {}
        changes["image_settings"][key] = value

    # Only add an action if something changed
    if changes:
      self.add_action(ActionType.UPDATE_SETTINGS, changes)
      # Update metadata
      self.metadata.update({"settings": self.settings.to_dict()})

  def get_settings(self) -> ConversationSettings:
    """
    Get the current conversation settings.

    Returns:
        ConversationSettings: The current settings
    """
    return self.settings

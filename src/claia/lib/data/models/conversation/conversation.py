"""
Conversation data model.

A pure data model representing a conversation between users and AI assistants,
with support for messages, tool definitions, settings, and audit trail actions.

This is a pure Python object that can exist in memory without file operations.
Persistence is handled separately by Repository classes.
"""

# External dependencies
from typing import Dict, Any, Optional, List, Union
import logging
import json
import time
import uuid

# Internal dependencies
from ....enums.conversation import ActionType, MessageRole
from ..text import TextFile
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


########################################################################
#                             CONVERSATION                             #
########################################################################
class Conversation(TextFile):
    """
    Pure data model for conversations.

    Extends TextFile to store conversation as JSON files, following the same
    pattern as Prompt. This eliminates code duplication and enables consistent
    file handling across the system.

    Represents a conversation with messages, tool definitions, settings,
    and an audit trail of actions. This is a pure Python object without
    file or database dependencies - persistence is handled by Repository classes.

    Features:
    - Message management (add, update, delete, search)
    - Tool definition management
    - Settings management
    - Action tracking for audit trail
    - System prompt generation with tool instructions
    - Streaming support via thread-safe message updates
    """

    def __init__(self,
                 id: Optional[str] = None,
                 title: str = DEFAULT_CONVERSATION_TITLE,
                 prompt: str = "",
                 tool_calling_prompt: Optional[str] = None,
                 messages: Optional[List[Union[Message, Dict[str, Any]]]] = None,
                 actions: Optional[List[Union[Action, Dict[str, Any]]]] = None,
                 tool_definitions: Optional[List[Union[ToolDefinition, Dict[str, Any]]]] = None,
                 settings: Optional[Union[ConversationSettings, Dict[str, Any]]] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None,
                 **kwargs):
        """
        Initialize a conversation.

        Args:
            id: Optional ID for the conversation (generated if not provided)
            title: Title of the conversation
            prompt: System prompt for the conversation
            tool_calling_prompt: Optional prompt for tool calling instructions
            messages: Optional list of initial messages
            actions: Optional list of initial actions
            tool_definitions: Optional list of tool definitions
            settings: Optional conversation settings
            created_at: Optional creation timestamp
            updated_at: Optional last update timestamp
            **kwargs: Additional arguments for TextFile (file_name handled by repository)
        """
        # Initialize TextFile - BaseFile handles ID generation and file naming
        # The file_name is primarily for persistence; repositories can override it
        super().__init__(
            file_name=kwargs.pop('file_name', f"conversation-{id or 'new'}"),
            file_id=id,  # BaseFile generates UUID if None
            mime_type='application/json',
            encoding='utf-8',
            created_at=created_at,
            updated_at=updated_at,
            **kwargs
        )
        
        # Conversation-specific fields
        self.title = title
        self.prompt = prompt
        self.tool_calling_prompt = tool_calling_prompt
        
        # Store conversation metadata in the file metadata
        self.metadata['title'] = title
        self.metadata['conversation_type'] = 'conversation'

        # Initialize messages
        self.messages: List[Message] = []
        if messages:
            for message_data in messages:
                if isinstance(message_data, Message):
                    self.messages.append(message_data)
                else:
                    self.messages.append(Message.from_dict(message_data))

        # Initialize actions
        self.actions: List[Action] = []
        if actions:
            for action_data in actions:
                if isinstance(action_data, Action):
                    self.actions.append(action_data)
                else:
                    self.actions.append(Action.from_dict(action_data))

        # Initialize tool definitions
        self.tool_definitions: List[ToolDefinition] = []
        if tool_definitions:
            for tool_data in tool_definitions:
                if isinstance(tool_data, ToolDefinition):
                    self.tool_definitions.append(tool_data)
                else:
                    self.tool_definitions.append(ToolDefinition.from_dict(tool_data))

        # Initialize settings
        if settings is None:
            self.settings = ConversationSettings()
        elif isinstance(settings, ConversationSettings):
            self.settings = settings
        else:
            self.settings = ConversationSettings.from_dict(settings)

        # If no actions are provided, create an initial action
        if not self.actions:
            self.add_action(ActionType.CREATE_CONVERSATION, {
                "title": self.title,
                "system_prompt": self.prompt,
                "tool_prompt": self.tool_calling_prompt
            })

    def get_file_type(self):
        """Override to return CONVERSATION file type."""
        from ....enums.file import FileSubdirectory
        return FileSubdirectory.CONVERSATION

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the conversation to a dictionary.

        Returns:
            Dict containing all conversation data for serialization
        """
        # Get base file data
        data = super().to_dict()
        
        # Add conversation-specific fields
        data.update({
            "title": self.title,
            "prompt": self.prompt,
            "tool_calling_prompt": self.tool_calling_prompt,
            "messages": [m.to_dict() for m in self.messages],
            "actions": [a.to_dict() for a in self.actions],
            "tool_definitions": [t.to_dict() for t in self.tool_definitions],
            "settings": self.settings.to_dict(),
        })
        
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """
        Create a conversation from a dictionary.

        Args:
            data: Dictionary containing conversation data

        Returns:
            Conversation: New conversation instance
        """
        return cls(
            id=data.get("id"),
            title=data.get("title", DEFAULT_CONVERSATION_TITLE),
            prompt=data.get("prompt", ""),
            tool_calling_prompt=data.get("tool_calling_prompt"),
            messages=data.get("messages", []),
            actions=data.get("actions", []),
            tool_definitions=data.get("tool_definitions", []),
            settings=data.get("settings"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            file_name=data.get("file_name"),
            is_reference=data.get("is_reference", False),
            source_path=data.get("source_path"),
            metadata=data.get("metadata", {})
        )

    def load_content(self) -> str:
        """
        Load conversation content as JSON string.
        
        Returns:
            str: JSON serialization of conversation data
        """
        if self._content_loaded and self._content is not None:
            return self._content
        
        # Generate content from current conversation state
        return self.content

    @property
    def content(self) -> str:
        """
        Get conversation content as JSON string.
        
        Returns:
            str: JSON serialization of conversation data
        """
        return json.dumps(self.to_dict(), indent=2)
    
    def set_content(self, content: str) -> None:
        """
        Set conversation content from JSON string.
        
        Args:
            content: JSON string containing conversation data
        """
        data = json.loads(content)
        
        # Update conversation fields from data
        self.title = data.get("title", self.title)
        self.prompt = data.get("prompt", self.prompt)
        self.tool_calling_prompt = data.get("tool_calling_prompt", self.tool_calling_prompt)
        
        # Update messages
        self.messages = []
        for message_data in data.get("messages", []):
            if isinstance(message_data, Message):
                self.messages.append(message_data)
            else:
                self.messages.append(Message.from_dict(message_data))
        
        # Update actions
        self.actions = []
        for action_data in data.get("actions", []):
            if isinstance(action_data, Action):
                self.actions.append(action_data)
            else:
                self.actions.append(Action.from_dict(action_data))
        
        # Update tool definitions
        self.tool_definitions = []
        for tool_data in data.get("tool_definitions", []):
            if isinstance(tool_data, ToolDefinition):
                self.tool_definitions.append(tool_data)
            else:
                self.tool_definitions.append(ToolDefinition.from_dict(tool_data))
        
        # Update settings
        settings_data = data.get("settings")
        if settings_data:
            if isinstance(settings_data, ConversationSettings):
                self.settings = settings_data
            else:
                self.settings = ConversationSettings.from_dict(settings_data)
        
        # Mark content as loaded
        self._content = content
        self._content_loaded = True
        self.size = len(content.encode(self.encoding))
        self.updated_at = time.time()

    # Message management methods

    def add_message(self, speaker: Union[MessageRole, str], content: str, 
                   file_ids: Optional[List[str]] = None) -> Message:
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
        message = Message(
            speaker=speaker,
            content=content,
            file_ids=file_ids or []
        )

        # Extract arguments from the message content
        message.extract_inline_args()

        self.messages.append(message)
        self.updated_at = time.time()

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

    def update_message(self, message_id: str, content: Optional[str] = None, 
                      file_ids: Optional[List[str]] = None) -> Optional[Message]:
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
        for message in self.messages:
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
                self.updated_at = time.time()

                # Prepare action metadata
                action_metadata = {
                    "message_id": message_id,
                    "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
                }

                # Add query args info to metadata if changed
                if content is not None:
                    action_metadata["inline_args_changed"] = (
                        had_inline_args_before != message.has_inline_args() or 
                        old_inline_args_count != len(message.inline_args)
                    )
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
                self.updated_at = time.time()

                # Add an action for this deletion
                self.add_action(ActionType.DELETE_MESSAGE, {
                    "message_id": message_id,
                    "speaker": deleted_message.speaker.value
                })

                return True

        logger.error(f"Message not found for deletion: {message_id}")
        return False

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
        """Get the latest message in the conversation."""
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

    def stream_message(self, message_id: str, content: str, append: bool = False, 
                      end: bool = False) -> Optional[Message]:
        """
        Update a message's content for streaming without adding an action.

        This method uses thread-safe message updates and is designed for streaming
        scenarios where a message is updated incrementally. It doesn't create actions
        for each update to avoid flooding the audit trail.

        On the first call for a given message_id, a START_STREAM action will be added.
        When end=True, an END_STREAM action will be added.

        Args:
            message_id: The ID of the message to update
            content: New content for the message
            append: If True, append the content; if False, replace it
            end: If True, mark the end of streaming

        Returns:
            Optional[Message]: The updated message, or None if not found
        """
        # Find the message
        for message in self.messages:
            if message.message_id == message_id:
                # Use thread-safe update methods
                if append:
                    message.safe_append_content(content)
                else:
                    message.safe_update_content(content)

                self.updated_at = time.time()

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

                # Add END_STREAM action if specified
                if end:
                    self.add_action(ActionType.END_STREAM, {
                        "message_id": message_id,
                        "speaker": message.speaker.value,
                        "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
                    })

                return message

        logger.error(f"Message not found for streaming update: {message_id}")
        return None

    # File attachment methods

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
        self.updated_at = time.time()

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
        self.updated_at = time.time()

        # Add an action for this file detachment
        self.add_action(ActionType.DETACH_FILE, {
            "message_id": message_id,
            "file_id": file_id
        })

        return True

    # Tool definition management methods

    def add_tool_definition(self, name: str, description: str, parameters: Dict[str, Any], 
                          returns: Dict[str, Any] = None) -> ToolDefinition:
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
        self.updated_at = time.time()

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
        for tool in self.tool_definitions:
            if tool.tool_id == tool_id:
                # Update tool properties if provided
                old_name = tool.name

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
                self.updated_at = time.time()

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
                self.updated_at = time.time()

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

    # Prompt and settings management

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

    def change_title(self, new_title: str) -> None:
        """
        Change the conversation title.

        Args:
            new_title: The new title for the conversation
        """
        old_title = self.title
        self.title = new_title
        self.updated_at = time.time()

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
        self.updated_at = time.time()

        # Add an action for this system prompt change
        self.add_action(ActionType.CHANGE_SYSTEM_PROMPT, {
            "old_prompt": old_prompt,
            "new_prompt": new_prompt
        })

    def set_tool_calling_prompt(self, prompt: str) -> None:
        """
        Set the tool calling prompt for this conversation.

        Args:
            prompt: The prompt used for tool calling detection/execution
        """
        old_prompt = self.tool_calling_prompt
        self.tool_calling_prompt = prompt
        self.updated_at = time.time()

        # Add action to track this change (tool prompt specific)
        self.add_action(ActionType.CHANGE_TOOL_PROMPT, {
            "old_prompt": old_prompt,
            "new_prompt": prompt
        })

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
            self.updated_at = time.time()
            self.add_action(ActionType.UPDATE_SETTINGS, changes)

    def get_settings(self) -> ConversationSettings:
        """
        Get the current conversation settings.

        Returns:
            ConversationSettings: The current settings
        """
        return self.settings

    # File management convenience methods

    def load_message_files(self, message_id: str, file_repo, load_content: bool = False) -> List:
        """
        Load all files attached to a message.

        Generic method that works with any file type (ImageFile, TextFile, etc.).

        Args:
            message_id: The ID of the message
            file_repo: FileRepository instance for loading files
            load_content: Whether to pre-load file content

        Returns:
            List[BaseFile]: List of files attached to the message
        """
        message = self.get_message(message_id)
        if not message:
            logger.warning(f"Message not found: {message_id}")
            return []

        if not message.file_ids:
            return []

        files = file_repo.load_multiple(message.file_ids, load_content=load_content)

        return files

    def load_all_files(self, file_repo, load_content: bool = False) -> Dict[str, List]:
        """
        Load all files for all messages in the conversation.

        Generic method that works with any file type.

        Args:
            file_repo: FileRepository instance for loading files
            load_content: Whether to pre-load file content

        Returns:
            Dict[str, List[BaseFile]]: Dictionary mapping message_id -> list of files
        """
        result = {}

        for message in self.messages:
            if message.file_ids:
                files = file_repo.load_multiple(message.file_ids, load_content=load_content)
                if files:
                    result[message.message_id] = files

        return result

    def get_all_file_ids(self) -> List[str]:
        """
        Get all file IDs referenced in this conversation.

        Returns:
            List[str]: List of all unique file IDs
        """
        file_ids = set()
        for message in self.messages:
            file_ids.update(message.file_ids)
        return list(file_ids)

    # Action tracking for audit trail

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


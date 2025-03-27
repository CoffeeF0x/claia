"""
This module contains the conversation file handling class for CLAIA.
"""

# External dependencies
import json
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Type, TypeVar, Union, List

# Internal dependencies
from .text import TextFile
from .base import BaseFile
from enums.file import FileSubdirectory
from enums.conversation import ActionType, MessageRole



########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_CONVERSATION_TITLE = "New Conversation"

# Default function format placeholder
DEFAULT_FUNCTION_FORMAT = """
[FUNCTION_CALL]{
"name": "function_name",
"parameters": {
  "param1": "value1",
  "param2": "value2"
}
}[/FUNCTION_CALL]
"""



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
    """
    
    def __init__(self, 
                 speaker: MessageRole, 
                 content: str, 
                 message_id: Optional[str] = None,
                 file_ids: Optional[List[str]] = None,
                 created_at: Optional[float] = None,
                 updated_at: Optional[float] = None):
        """
        Initialize a message.
        
        Args:
            speaker: The speaker of the message
            content: The content of the message
            message_id: Optional ID for the message (generated if not provided)
            file_ids: Optional list of file IDs attached to the message
            created_at: Optional timestamp for creation time
            updated_at: Optional timestamp for last update time
        """
        self.message_id = message_id or str(uuid.uuid4())
        self.speaker = speaker if isinstance(speaker, MessageRole) else MessageRole(speaker)
        self.content = content
        self.file_ids = file_ids or []
        self.created_at = created_at or time.time()
        self.updated_at = updated_at or self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        return {
            "message_id": self.message_id,
            "speaker": self.speaker.value,
            "content": self.content,
            "file_ids": self.file_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at
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
    - Inherits text file functionality for content operations
    """
    
    def __init__(self, base_directory: str, **kwargs):
        """
        Initialize a conversation file.
        
        Args:
            base_directory: Base directory for the file
            **kwargs: Additional arguments to pass to the parent class
        """
        # Extract conversation-specific kwargs
        self.title = kwargs.pop("title", DEFAULT_CONVERSATION_TITLE)
        self.prompt = kwargs.pop("prompt", "")
        initial_messages = kwargs.pop("messages", [])
        initial_actions = kwargs.pop("actions", [])
        
        # Ensure the file has .json extension
        file_name = kwargs.get("file_name")
        if file_name and not file_name.endswith(".json"):
            kwargs["file_name"] = f"{file_name}.json"
        
        # Initialize as TextFile but ensure mime_type is application/json
        kwargs["mime_type"] = "application/json"
        super().__init__(base_directory=base_directory, **kwargs)
        
        # Initialize messages and actions
        self.messages = []
        self.actions = []
        
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
        
        # If no actions are provided, create an initial action
        if not self.actions:
            self.add_action(ActionType.CREATE_CONVERSATION, {
                "title": self.title,
                "prompt": self.prompt
            })
        
        # Add conversation-specific metadata
        self.metadata.update({
            "title": self.title,
            "message_count": len(self.messages)
        })
    
    def get_subdirectory(self) -> str:
        """
        Override to return the conversations subdirectory.
        
        Returns:
            str: The conversations subdirectory
        """
        return "conversations"
    
    def get_conversation_data(self) -> Dict[str, Any]:
        """
        Get the conversation data as a dictionary.
        
        Returns:
            Dict[str, Any]: Conversation data
        """
        # If already loaded, return cached data
        if hasattr(self, '_conversation_data'):
            return self._conversation_data
        
        # Try to load from file if it exists
        if self.exists():
            try:
                content = self.get_content()
                data = json.loads(content)
                
                # Update title and prompt from data
                self.title = data.get("title", DEFAULT_CONVERSATION_TITLE)
                self.prompt = data.get("prompt", "")
                
                # Update messages and actions from data
                self.messages = [Message.from_dict(m) for m in data.get("messages", [])]
                self.actions = [Action.from_dict(a) for a in data.get("actions", [])]
                
                # Update metadata
                self.metadata.update({
                    "title": self.title,
                    "message_count": len(self.messages)
                })
                
                # Cache the data
                self._conversation_data = data
                return data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from conversation file: {self.file_id}")
        
        # Return default data if file doesn't exist or parsing failed
        default_data = self.to_dict()
        self._conversation_data = default_data
        return default_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the conversation to a dictionary."""
        return {
            "conversation_id": self.file_id,
            "title": self.title,
            "prompt": self.prompt,
            "messages": [m.to_dict() for m in self.messages],
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.timestamp
        }
    
    def to_json(self) -> str:
        """
        Convert the conversation to a JSON string.
        
        Returns:
            str: JSON representation of the conversation
        """
        # Construct conversation data
        conversation_data = self.to_dict()
        
        # Update cached data
        self._conversation_data = conversation_data
        
        # Update metadata
        self.metadata.update({
            "title": self.title,
            "message_count": len(self.messages)
        })
        
        # Convert to JSON string
        return json.dumps(conversation_data, indent=2)
    
    def _get_default_content(self) -> Optional[str]:
        """
        Provide default content when saving without content.
        
        Returns:
            str: JSON representation of the conversation
        """
        return self.to_json()
    
    def apply_substitutions(self, text: str, **kwargs) -> str:
        """
        Apply substitutions to the given text, replacing placeholders with values.
        
        This generic substitution system handles:
        1. Simple placeholders like {name} or {date}
        2. Function definition placeholders {function_definitions}
        3. Function format placeholders {function_format}
        4. Any other placeholders passed via kwargs
        
        Args:
            text: The text containing placeholders to replace
            **kwargs: Keyword arguments mapping placeholder names to values
            
        Returns:
            str: The text with all matched placeholders replaced
        """
        # Make a copy of the text to avoid modifying the original
        processed_text = text
        
        # Handle function definitions placeholder
        if "{function_definitions}" in processed_text and "function_definitions" not in kwargs:
            # If function_definitions is not in kwargs but we have them stored, use them
            if hasattr(self, 'function_definitions'):
                function_definitions_json = json.dumps(self.function_definitions, indent=2)
                kwargs["function_definitions"] = function_definitions_json
        
        # Handle function format placeholder
        if "{function_format}" in processed_text and "function_format" not in kwargs:
            kwargs["function_format"] = DEFAULT_FUNCTION_FORMAT
        
        # Only attempt formatting if there are placeholders to replace
        if kwargs and any(f"{{{key}}}" in processed_text for key in kwargs):
            try:
                processed_text = processed_text.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing key in text substitution: {e}")
            except Exception as e:
                logger.error(f"Error during text substitution: {e}")
        
        return processed_text
    
    def format_prompt(self, **kwargs) -> str:
        """
        Format the conversation prompt with the given replacements.
        
        This is a convenience wrapper around apply_substitutions that uses
        the conversation's prompt as the text.
        
        Args:
            **kwargs: Keyword arguments for string formatting
            
        Returns:
            str: The formatted prompt
        """
        return self.apply_substitutions(self.prompt, **kwargs)
    
    def process_message(self, message_id: str, **kwargs) -> str:
        """
        Process a message's content by applying substitutions.
        
        Args:
            message_id: The ID of the message to process
            **kwargs: Substitution key-value pairs
            
        Returns:
            str: The processed message content, or empty string if message not found
        """
        message = self.get_message(message_id)
        if not message:
            logger.warning(f"Cannot process message: message not found with ID {message_id}")
            return ""
        
        return self.apply_substitutions(message.content, **kwargs)
    
    def load_function_definitions(self, function_definitions: List[Dict[str, Any]]) -> None:
        """
        Load function definitions into the conversation.
        This should be called before using format_prompt if function definitions are needed.

        Args:
            function_definitions: List of function definitions to load
        """
        self.function_definitions = function_definitions
        logger.debug(f"Loaded {len(function_definitions)} function definitions into conversation")
    
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
        self.messages.append(message)
        
        # Add an action for this message
        self.add_action(ActionType.CREATE_MESSAGE, {
            "message_id": message.message_id,
            "speaker": message.speaker.value,
            "content_preview": content[:50] + "..." if len(content) > 50 else content
        })
        
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
                # Update message properties if provided
                if content is not None:
                    message.content = content
                if file_ids is not None:
                    message.file_ids = file_ids
                
                # Update timestamp
                message.updated_at = time.time()
                
                # Add an action for this update
                self.add_action(ActionType.UPDATE_MESSAGE, {
                    "message_id": message_id,
                    "content_preview": message.content[:50] + "..." if len(message.content) > 50 else message.content
                })
                
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
    
    def get_messages(self, speaker: Optional[MessageRole] = None) -> List[Message]:
        """
        Get all messages, optionally filtered by speaker.
        
        Args:
            speaker: Optional speaker to filter by
            
        Returns:
            List[Message]: List of matching messages
        """
        if speaker is None:
            return self.messages
        
        return [m for m in self.messages if m.speaker == speaker]
    
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
            "old_prompt": old_prompt[:50] + "..." if len(old_prompt) > 50 else old_prompt,
            "new_prompt": new_prompt[:50] + "..." if len(new_prompt) > 50 else new_prompt
        })
    
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
    
    def _post_save_hook(self):
        """
        Update conversation statistics after saving.
        
        This is called automatically after save() completes.
        """
        # Call parent's post save hook for text stats
        super()._post_save_hook()
        
        # Only update conversation data if the file exists
        if self.exists():
            # Clear cached data to force refresh
            if hasattr(self, '_conversation_data'):
                delattr(self, '_conversation_data')
            
            # Reload conversation data to ensure everything is in sync
            self.get_conversation_data()
    
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
        conversation = cls.load(conversation_id, base_directory)
        if conversation:
            # Load conversation data explicitly
            conversation.get_conversation_data()
            return conversation
        
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
            subdirectory="conversations"
        )
        
        # Extract metadata
        return [metadata for _, metadata in conversations.items()] 
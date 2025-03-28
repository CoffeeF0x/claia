"""
This module contains the conversation file handling class for CLAIA.
"""

# TODO:
# - Attach a file should just send the path or url along with whether or not
#   it's a reference (optional), then identify and call the correct object
#   to attach the file. If a file id is passed, then validate and identify the type
# - Consider redesign so that an external file load is not required (ie, stored fully 
#   in memory except on saves and loads)

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
               tool_id: Optional[str] = None,
               created_at: Optional[float] = None,
               updated_at: Optional[float] = None):
    """
    Initialize a tool definition.
    
    Args:
        name: The name of the tool
        description: The description of the tool
        parameters: The parameters of the tool
        tool_id: Optional ID for the tool (generated if not provided)
        created_at: Optional timestamp for creation time
        updated_at: Optional timestamp for last update time
    """
    self.tool_id = tool_id or str(uuid.uuid4())
    self.name = name
    self.description = description
    self.parameters = parameters
    self.created_at = created_at or time.time()
    self.updated_at = updated_at or self.created_at
  
  def to_dict(self) -> Dict[str, Any]:
    """Convert the tool definition to a dictionary."""
    return {
      "tool_id": self.tool_id,
      "name": self.name,
      "description": self.description,
      "parameters": self.parameters,
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
    initial_tools = kwargs.pop("tool_definitions", [])
    
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
      "tool_count": len(self.tool_definitions)
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
      "created_at": self.timestamp
    }
    
    return json.dumps(content_data, indent=2)
  
  def _post_save_hook(self):
    """
    Update conversation metadata after saving.
    
    This is called automatically after save() completes.
    """
    # Call parent's post save hook for text stats
    super()._post_save_hook()
    
    # Update metadata based on current object state
    self.metadata.update({
      "title": self.title,
      "message_count": len(self.messages),
      "tool_count": len(self.tool_definitions)
    })
    
    # Save metadata to ensure it's up to date in the manifest
    self.save_metadata()

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
            "parameters": t.parameters
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
  
  def add_tool_definition(self, name: str, description: str, parameters: Dict[str, Any]) -> ToolDefinition:
    """
    Add a tool definition to the conversation.
    
    Args:
        name: The name of the tool
        description: The description of the tool
        parameters: The parameters of the tool
        
    Returns:
        ToolDefinition: The created tool definition
    """
    # First check if a tool with the same name already exists
    for tool in self.tool_definitions:
      if tool.name == name:
        logger.warning(f"Tool with name '{name}' already exists. Use update_tool_definition instead.")
        return tool
        
    # Create a new tool definition
    tool_def = ToolDefinition(name=name, description=description, parameters=parameters)
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
                                parameters: Optional[Dict[str, Any]] = None) -> Optional[ToolDefinition]:
    """
    Update a tool definition in the conversation.
    
    Args:
        tool_id: The ID of the tool to update
        name: Optional new name for the tool
        description: Optional new description for the tool
        parameters: Optional new parameters for the tool
        
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
        "parameters": t.parameters
      }
      for t in self.tool_definitions
    ]

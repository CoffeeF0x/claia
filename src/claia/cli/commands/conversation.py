"""
Conversation command class for the CLAIA CLI.

This module contains the command class for managing conversations
(list, load, clear, set title, delete).
Delegates to cli.conversation_* tools via the registry.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.lib.results import Result
from claia.lib.data.models import Conversation
from claia.lib.data.repositories import FileSystemRepository
from claia.lib.enums.conversation import MessageRole
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Constants for formatted output
CONVERSATION_WARNING = "⚠️  WARNING"


class ConversationCommand(BaseCommand):
  """Command to manage conversations. Delegates to cli.conversation_* tools."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the conversation command.
    
    Args:
        args: List of arguments (subcommand and additional args)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result indicating success/failure
    """
    self.logger.debug("Conversation command received")
    
    # If no args, show usage and current conversation
    if not args:
      return self._show_usage()
    
    subcommand = args[0].lower()
    
    # Route to appropriate subcommand handler
    handlers = {
      'list': self._list_conversations,
      'clear': self._clear_conversation,
      'new': self._clear_conversation,  # alias for clear
      'load': lambda: self._load_conversation(args[1:]),
      'title': lambda: self._set_title(args[1:]),
      'delete': lambda: self._delete_conversation(args[1:]),
      'print': self._print_conversation,
      'details': self._show_details,
    }
    
    handler = handlers.get(subcommand)
    if handler:
      return handler()
    else:
      output = f"Unknown conversation subcommand: {subcommand}\n"
      output += f"Use {self.format_command('conversation')} to see available subcommands."
      return Result(success=False, message=output)
  
  def _get_tool_params(self) -> Dict[str, Any]:
    """Get common parameters to pass to cli tools."""
    return {
      'files_directory': self.settings.files_directory,
      'active_conversation_id': self.settings.active_conversation.id if self.settings.active_conversation else None,
      'conversation': self.settings.active_conversation,
    }
  
  def _show_usage(self) -> Result:
    """Show usage information and current conversation."""
    output_lines = []
    
    if self.settings.active_conversation:
      output_lines.append(f"\nActive conversation: {self.settings.active_conversation.title}")
      output_lines.append(f"  ID: {self.settings.active_conversation.id}")
      msg_count = len(self.settings.active_conversation.messages)
      output_lines.append(f"  Messages: {msg_count}")
    else:
      output_lines.append("\nNo active conversation")
    
    output_lines.append("\nUsage:")
    prefix = self.get_help_prefix()
    
    output_lines.append(f"  {prefix}conversation list              - List all saved conversations")
    output_lines.append(f"  {prefix}conversation print             - Print the entire active conversation")
    output_lines.append(f"  {prefix}conversation details           - Show metadata/technical info")
    output_lines.append(f"  {prefix}conversation load <id|title>   - Load a specific conversation")
    output_lines.append(f"  {prefix}conversation clear/new         - Clear active and start new conversation")
    output_lines.append(f"  {prefix}conversation title <title>     - Set title of active conversation")
    output_lines.append(f"  {prefix}conversation delete <id|title> - Delete a saved conversation")
    
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _list_conversations(self) -> Result:
    """List all saved conversations via cli.conversation_list tool."""
    params = self._get_tool_params()
    return self.registry.run_command('cli.conversation_list', params, None)
  
  def _print_conversation(self) -> Result:
    """Print the entire active conversation via cli.conversation_print tool."""
    params = self._get_tool_params()
    return self.registry.run_command('cli.conversation_print', params, None)
  
  def _show_details(self) -> Result:
    """Show metadata and technical info via cli.conversation_details tool."""
    params = self._get_tool_params()
    return self.registry.run_command('cli.conversation_details', params, None)
  
  def _clear_conversation(self) -> Result:
    """Clear the active conversation and start a new one."""
    old_title = None
    if self.settings.active_conversation:
      old_title = self.settings.active_conversation.title
    
    self.settings.active_conversation = None
    
    if old_title:
      output = f"Cleared conversation: {old_title}"
      output += "\nStarting a new conversation."
    else:
      output = "Starting a new conversation."
    
    return Result(success=True, data=output)
  
  def _load_conversation(self, args: List[str]) -> Result:
    """
    Load a specific conversation by ID or title.
    
    Args:
        args: List containing the conversation ID or title
    
    Returns:
        Result indicating success/failure
    """
    if not args:
      output = f"Missing conversation identifier. Usage: {self.format_command('conversation load <id|title>')}"
      return Result(success=False, message=output)
    
    identifier = ' '.join(args)  # Allow multi-word titles
    
    try:
      file_repo = FileSystemRepository(self.settings.files_directory)
      
      # Try to load by ID first
      conversation = file_repo.load(identifier, load_content=True)
      
      # If not found by ID, search by title
      if not conversation:
        conversations = file_repo.list_all(file_type='conversations')
        
        for conv_meta in conversations:
          if conv_meta.get('title', '').lower() == identifier.lower():
            conv_id = conv_meta.get('id')
            conversation = file_repo.load(conv_id, load_content=True)
            break
      
      if not conversation:
        output = f"Conversation not found: {identifier}\n"
        output += f"Use {self.format_command('conversation list')} to see available conversations."
        return Result(success=False, message=output)
      
      # Ensure it's a Conversation object
      if not isinstance(conversation, Conversation):
        return Result(success=False, message=f"Loaded object is not a conversation: {type(conversation)}")
      
      self.settings.active_conversation = conversation
      
      output = f"\nLoaded conversation: {conversation.title}"
      output += f"\n  ID: {conversation.id}"
      output += f"\n  Messages: {len(conversation.messages)}"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error loading conversation '{identifier}': {str(e)}"
      self.logger.error(f"Error loading conversation: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _set_title(self, args: List[str]) -> Result:
    """
    Set the title of the active conversation.
    
    Args:
        args: List containing the new title
    
    Returns:
        Result indicating success/failure
    """
    if not self.settings.active_conversation:
      return Result(success=False, message="No active conversation to set title for.")
    
    if not args:
      output = f"Missing title. Usage: {self.format_command('conversation title <new_title>')}"
      return Result(success=False, message=output)
    
    new_title = ' '.join(args)
    old_title = self.settings.active_conversation.title
    
    try:
      self.settings.active_conversation.title = new_title
      self.settings.active_conversation.metadata['title'] = new_title
      
      # Save the conversation with the new title
      file_repo = FileSystemRepository(self.settings.files_directory)
      file_repo.save(self.settings.active_conversation)
      
      output = f"\nConversation title updated:"
      output += f"\n  {old_title} → {new_title}"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error setting conversation title: {str(e)}"
      self.logger.error(f"Error setting title: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _delete_conversation(self, args: List[str]) -> Result:
    """
    Delete a saved conversation.
    
    Args:
        args: List containing conversation ID or title
    
    Returns:
        Result indicating success/failure
    """
    if not args:
      output = f"Missing conversation identifier. Usage: {self.format_command('conversation delete <id|title>')}"
      return Result(success=False, message=output)
    
    identifier = ' '.join(args)
    
    try:
      file_repo = FileSystemRepository(self.settings.files_directory)
      
      # Try to find the conversation
      conv_id = None
      conv_title = None
      
      # Try as ID first
      conversation = file_repo.load(identifier, load_content=False)
      if conversation and isinstance(conversation, Conversation):
        conv_id = conversation.id
        conv_title = conversation.title
      else:
        # Search by title
        conversations = file_repo.list_all(file_type='conversations')
        for conv_meta in conversations:
          if conv_meta.get('title', '').lower() == identifier.lower():
            conv_id = conv_meta.get('id')
            conv_title = conv_meta.get('title')
            break
      
      if not conv_id:
        output = f"Conversation not found: {identifier}"
        return Result(success=False, message=output)
      
      # Check if it's the active conversation
      if (self.settings.active_conversation and 
          self.settings.active_conversation.id == conv_id):
        output = f"Cannot delete the active conversation '{conv_title}'.\n"
        output += f"Use {self.format_command('conversation clear')} first."
        return Result(success=False, message=output)
      
      # Ask for confirmation
      print(f"\n{CONVERSATION_WARNING}: You are about to delete conversation '{conv_title}'.")
      print("This action cannot be undone.")
      
      try:
        confirmation = input("\nType 'DELETE' to confirm deletion: ").strip()
        
        if confirmation != 'DELETE':
          return Result(success=True, message="Deletion cancelled.")
        
        # Delete the conversation
        if file_repo.delete(conv_id):
          output = f"Successfully deleted conversation: {conv_title}"
          return Result(success=True, data=output)
        else:
          return Result(success=False, message=f"Failed to delete conversation: {conv_title}")
          
      except (KeyboardInterrupt, EOFError):
        print("\n\nDeletion cancelled.")
        return Result(success=True, message="Deletion cancelled by user")
      
    except Exception as e:
      output = f"Error deleting conversation '{identifier}': {str(e)}"
      self.logger.error(f"Error deleting conversation: {e}", exc_info=True)
      return Result(success=False, message=output)


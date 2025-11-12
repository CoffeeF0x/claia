"""
Conversation command class for the CLAIA CLI.

This module contains the command class for managing conversations
(list, load, clear, set title, delete).
"""

import logging
from typing import List, Optional, Any

from claia.lib.results import Result
from claia.lib.data.models import Conversation
from claia.lib.data.repositories import FileSystemRepository
from claia.lib.enums.conversation import MessageRole
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Constants for formatted output
CONVERSATION_DIVIDER = "-" * 70
CONVERSATION_WARNING = "⚠️  WARNING"


class ConversationCommand(BaseCommand):
  """Command to manage conversations."""
  
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
    """List all saved conversations."""
    try:
      file_repo = FileSystemRepository(self.settings.files_directory)
      conversations = file_repo.list_all(file_type='conversations')
      
      if not conversations:
        return Result(success=True, data="No saved conversations found.")
      
      output_lines = []
      output_lines.append("\nSaved conversations:")
      output_lines.append(CONVERSATION_DIVIDER)
      
      # Sort by updated_at (most recent first)
      conversations.sort(key=lambda c: c.get('updated_at', 0), reverse=True)
      
      for conv_meta in conversations:
        conv_id = conv_meta.get('id', 'Unknown')
        title = conv_meta.get('title', 'Untitled')
        updated_at = conv_meta.get('updated_at', 0)
        
        # Mark the current active conversation
        marker = " (active)" if (self.settings.active_conversation and 
                                 self.settings.active_conversation.id == conv_id) else ""
        
        # Format timestamp
        import time
        time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(updated_at)) if updated_at else "Unknown"
        
        output_lines.append(f"  • {title}{marker}")
        output_lines.append(f"    ID: {conv_id}")
        output_lines.append(f"    Updated: {time_str}")
      
      output_lines.append("")
      output = "\n".join(output_lines)
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error listing conversations: {str(e)}"
      self.logger.error(f"Error listing conversations: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _print_conversation(self) -> Result:
    """Print the entire active conversation with all messages."""
    if not self.settings.active_conversation:
      return Result(success=True, data="No active conversation.")
    
    conv = self.settings.active_conversation
    output_lines = []
    
    # Title header
    output_lines.append(f"\n{'=' * 70}")
    output_lines.append(f"{conv.title.center(70)}")
    output_lines.append(f"{'=' * 70}\n")
    
    # Show each message
    if not conv.messages:
      output_lines.append("(No messages in conversation)")
    else:
      for i, msg in enumerate(conv.messages):
        # Prettify the role
        role = self._prettify_role(msg.speaker)
        
        # Add message header
        output_lines.append(f"[{role}]")
        output_lines.append("-" * 70)
        
        # Add message content
        if msg.content:
          output_lines.append(msg.content)
        else:
          output_lines.append("(empty message)")
        
        # Add spacing between messages (except after last one)
        if i < len(conv.messages) - 1:
          output_lines.append("")
    
    output_lines.append("")
    output_lines.append(f"{'=' * 70}")
    output_lines.append(f"{f'{len(conv.messages)} message(s)'.center(70)}")
    output_lines.append(f"{'=' * 70}\n")
    
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _show_details(self) -> Result:
    """Show metadata and technical information about the current conversation."""
    if not self.settings.active_conversation:
      return Result(success=True, data="No active conversation.")
    
    conv = self.settings.active_conversation
    output_lines = []
    output_lines.append(f"\nConversation Details:")
    output_lines.append(CONVERSATION_DIVIDER)
    output_lines.append(f"  Title: {conv.title}")
    output_lines.append(f"  ID: {conv.id}")
    output_lines.append(f"  Messages: {len(conv.messages)}")
    
    # Show creation and update time
    import time
    if conv.created_at:
      created_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(conv.created_at))
      output_lines.append(f"  Created: {created_str}")
    if conv.updated_at:
      updated_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(conv.updated_at))
      output_lines.append(f"  Updated: {updated_str}")
    
    # Show prompt if present
    if conv.prompt and conv.prompt.get('system'):
      prompt_preview = conv.prompt['system'][:100]
      if len(conv.prompt['system']) > 100:
        prompt_preview += "..."
      output_lines.append(f"\n  System Prompt: {prompt_preview}")
    
    # Show settings if present
    if conv.settings:
      output_lines.append(f"\n  Settings:")
      if hasattr(conv.settings, 'model'):
        output_lines.append(f"    Model: {conv.settings.model or 'None'}")
      if hasattr(conv.settings, 'temperature'):
        output_lines.append(f"    Temperature: {conv.settings.temperature}")
      if hasattr(conv.settings, 'max_tokens'):
        output_lines.append(f"    Max Tokens: {conv.settings.max_tokens or 'Default'}")
    
    # Show tool definitions count if present
    if hasattr(conv, 'tool_definitions') and conv.tool_definitions:
      output_lines.append(f"\n  Tool Definitions: {len(conv.tool_definitions)}")
    
    # Show actions count if present
    if hasattr(conv, 'actions') and conv.actions:
      output_lines.append(f"  Actions (audit trail): {len(conv.actions)}")
    
    # Show message breakdown by role
    if conv.messages:
      role_counts = {}
      for msg in conv.messages:
        role_name = self._prettify_role(msg.speaker)
        role_counts[role_name] = role_counts.get(role_name, 0) + 1
      
      output_lines.append(f"\n  Message Breakdown:")
      for role, count in sorted(role_counts.items()):
        output_lines.append(f"    {role}: {count}")
    
    output_lines.append("")
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _prettify_role(self, role) -> str:
    """
    Convert a MessageRole enum to a prettified string.
    
    Args:
        role: MessageRole enum or string
    
    Returns:
        Prettified role string
    """
    if isinstance(role, MessageRole):
      role_str = role.value
    else:
      role_str = str(role).lower()
    
    # Capitalize first letter
    return role_str.capitalize()
  
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


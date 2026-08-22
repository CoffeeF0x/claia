"""
Conversation command for managing conversations.
"""

import logging
from typing import List, Optional, Any, Dict

from ...core.results import Result
from ...core.data.models import Conversation
from ..storage import JsonStore
from .base import BaseCommand


logger = logging.getLogger(__name__)


class ConversationCommand(BaseCommand):
  """Command to manage conversations (list, load, clear, title, delete)."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute conversation command: show usage or route to subcommand."""
    if not args:
      return self._show_usage()
    
    subcommand = args[0].lower()
    handlers = {
      'list': self._list_conversations,
      'clear': self._clear_conversation,
      'new': self._clear_conversation,
      'load': lambda: self._load_conversation(args[1:]),
      'title': lambda: self._set_title(args[1:]),
      'delete': lambda: self._delete_conversation(args[1:]),
      'print': self._print_conversation,
      'details': self._show_details,
    }
    
    handler = handlers.get(subcommand)
    if handler:
      return handler()
    return Result(success=False, message=f"Unknown conversation subcommand: {subcommand}\nUse {self.format_command('conversation')} to see available subcommands.")
  
  def _get_tool_params(self) -> Dict[str, Any]:
    """Get common parameters for cli tools."""
    return {
      'files_directory': self.settings.files_directory,
      'active_conversation_id': self.settings.active_conversation.id if self.settings.active_conversation else None,
      'conversation': self.settings.active_conversation,
    }
  
  def _show_usage(self) -> Result:
    """Show usage information and current conversation."""
    prefix = self.get_help_prefix()
    conv = self.settings.active_conversation
    
    lines = []
    if conv:
      lines.extend([
        f"\nActive conversation: {conv.title}",
        f"  ID: {conv.id}",
        f"  Messages: {len(conv.messages)}"
      ])
    else:
      lines.append("\nNo active conversation")
    
    lines.extend([
      "\nUsage:",
      f"  {prefix}conversation list              - List all saved conversations",
      f"  {prefix}conversation print             - Print the entire active conversation",
      f"  {prefix}conversation details           - Show metadata/technical info",
      f"  {prefix}conversation load <id|title>   - Load a specific conversation",
      f"  {prefix}conversation clear/new         - Drop the active conversation (next query starts a new one)",
      f"  {prefix}conversation title <title>     - Set title of active conversation",
      f"  {prefix}conversation delete <id|title> - Delete a saved conversation",
    ])
    return Result(success=True, data="\n".join(lines))
  
  def _list_conversations(self) -> Result:
    """List all saved conversations."""
    return self.registry.run_command('cli.conversation_list', self._get_tool_params(), None)
  
  def _print_conversation(self) -> Result:
    """Print the entire active conversation."""
    return self.registry.run_command('cli.conversation_print', self._get_tool_params(), None)
  
  def _show_details(self) -> Result:
    """Show metadata and technical info."""
    return self.registry.run_command('cli.conversation_details', self._get_tool_params(), None)
  
  def _clear_conversation(self) -> Result:
    """Drop the active conversation. The next query creates a new one."""
    old_title = self.settings.active_conversation.title if self.settings.active_conversation else None
    self.settings.active_conversation = None

    if old_title:
      return Result(
        success=True,
        data=f"Cleared conversation: {old_title}. The next query starts a new one.",
      )
    return Result(success=True, data="No active conversation.")
  
  def _load_conversation(self, args: List[str]) -> Result:
    """Load a specific conversation by ID or title."""
    if not args:
      return Result(success=False, message=f"Missing conversation identifier. Usage: {self.format_command('conversation load <id|title>')}")
    
    identifier = ' '.join(args)
    
    try:
      file_repo = JsonStore(self.settings.files_directory)
      
      # Try by ID first
      conv = file_repo.load(identifier)
      
      # If not found, try by title
      if not conv:
        conversations = file_repo.list_all(artifact_type='conversations')
        for meta in conversations:
          if meta.get('title', '').lower() == identifier.lower():
            conv = file_repo.load(meta.get('id'))
            break
      
      if not conv:
        return Result(success=False, message=f"Conversation not found: {identifier}\nUse {self.format_command('conversation list')} to see available conversations.")
      
      if not isinstance(conv, Conversation):
        return Result(success=False, message=f"Loaded object is not a conversation: {type(conv)}")
      
      self.settings.active_conversation = conv
      return Result(success=True, data=f"\nLoaded conversation: {conv.title}\n  ID: {conv.id}\n  Messages: {len(conv.messages)}")
      
    except Exception as e:
      self.logger.error(f"Error loading conversation: {e}", exc_info=True)
      return Result(success=False, message=f"Error loading conversation '{identifier}': {str(e)}")
  
  def _set_title(self, args: List[str]) -> Result:
    """Set the title of the active conversation."""
    if not self.settings.active_conversation:
      return Result(success=False, message="No active conversation to set title for.")
    
    if not args:
      return Result(success=False, message=f"Missing title. Usage: {self.format_command('conversation title <new_title>')}")
    
    new_title = ' '.join(args)
    old_title = self.settings.active_conversation.title
    
    try:
      self.settings.active_conversation.change_title(new_title)
      
      file_repo = JsonStore(self.settings.files_directory)
      file_repo.save(self.settings.active_conversation)
      
      return Result(success=True, data=f"\nConversation title updated:\n  {old_title} → {new_title}")
      
    except Exception as e:
      self.logger.error(f"Error setting title: {e}", exc_info=True)
      return Result(success=False, message=f"Error setting conversation title: {str(e)}")
  
  def _delete_conversation(self, args: List[str]) -> Result:
    """Delete a saved conversation with confirmation."""
    if not args:
      return Result(success=False, message=f"Missing conversation identifier. Usage: {self.format_command('conversation delete <id|title>')}")
    
    identifier = ' '.join(args)
    
    try:
      file_repo = JsonStore(self.settings.files_directory)
      
      # Find conversation
      conv_id, conv_title = None, None
      conv = file_repo.load(identifier)
      
      if conv and isinstance(conv, Conversation):
        conv_id, conv_title = conv.id, conv.title
      else:
        conversations = file_repo.list_all(artifact_type='conversations')
        for meta in conversations:
          if meta.get('title', '').lower() == identifier.lower():
            conv_id, conv_title = meta.get('id'), meta.get('title')
            break
      
      if not conv_id:
        return Result(success=False, message=f"Conversation not found: {identifier}")
      
      # Can't delete active conversation
      if self.settings.active_conversation and self.settings.active_conversation.id == conv_id:
        return Result(success=False, message=f"Cannot delete the active conversation '{conv_title}'.\nUse {self.format_command('conversation clear')} first.")
      
      # Confirmation
      print(f"\n⚠️  WARNING: You are about to delete conversation '{conv_title}'.")
      print("This action cannot be undone.")
      
      try:
        confirmation = input("\nType 'DELETE' to confirm deletion: ").strip()
        if confirmation != 'DELETE':
          return Result(success=True, message="Deletion cancelled.")
        
        if file_repo.delete(conv_id):
          return Result(success=True, data=f"Successfully deleted conversation: {conv_title}")
        return Result(success=False, message=f"Failed to delete conversation: {conv_title}")
        
      except (KeyboardInterrupt, EOFError):
        print("\n\nDeletion cancelled.")
        return Result(success=True, message="Deletion cancelled by user")
      
    except Exception as e:
      self.logger.error(f"Error deleting conversation: {e}", exc_info=True)
      return Result(success=False, message=f"Error deleting conversation '{identifier}': {str(e)}")

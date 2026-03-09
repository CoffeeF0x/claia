"""
Agent and Prompt commands for the CLAIA CLI.
"""

import logging
from typing import List, Optional, Any, Dict

from claia.lib.results import Result
from claia.lib.data.models import Prompt
from claia.cli.storage import FileSystemStore
from .base import BaseCommand


logger = logging.getLogger(__name__)


class AgentCommand(BaseCommand):
  """Command to manage active agent selection."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute agent command: show current, list, or switch agents."""
    if not args:
      return self._show_current_agent()
    if args[0].lower() == "list":
      return self._list_agents()
    return self._switch_agent(args[0])
  
  def _get_tool_params(self) -> Dict[str, Any]:
    """Get common parameters for cli tools."""
    return {
      'active_agent': self.settings.active_agent,
      'default_agent': self.settings.default_agent,
      'registry': self.registry,
    }
  
  def _show_current_agent(self) -> Result:
    """Show the current active agent with usage info."""
    result = self.registry.run_command('cli.agent_current', self._get_tool_params(), None)
    if not result.is_success():
      return result
    
    prefix = self.get_help_prefix()
    output = result.get_data() or ""
    output += f"\n\nUsage:\n  {prefix}agent list          - List all available agents"
    output += f"\n  {prefix}agent <agent_name>  - Switch to specified agent"
    return Result(success=True, data=output)
  
  def _list_agents(self) -> Result:
    """List all available agents."""
    return self.registry.run_command('cli.agent_list', self._get_tool_params(), None)
  
  def _switch_agent(self, agent_name: str) -> Result:
    """Switch to a specified agent."""
    agent_name = agent_name.lower()
    
    try:
      agent_class = self.registry.get_agent_class(agent_name)
      if not agent_class:
        return Result(success=False, message=f"Unknown agent: {agent_name}\nUse {self.format_command('agent list')} to see available agents.")
      
      old_agent = self.settings.active_agent
      self.settings.active_agent = agent_name
      
      output = f"\nActive agent changed: {old_agent or 'None'} -> {agent_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: {self.format_command(f'set default_agent {agent_name}')}"
      return Result(success=True, data=output)
      
    except Exception as e:
      self.logger.error(f"Error switching agent: {e}", exc_info=True)
      return Result(success=False, message=f"Error switching to agent '{agent_name}': {str(e)}")


class PromptCommand(BaseCommand):
  """Command to manage prompts (list, set, clear, delete, print)."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """Execute prompt command: show usage or route to subcommand."""
    if not args:
      return self._show_usage()
    
    subcommand = args[0].lower()
    handlers = {
      'list': self._list_prompts,
      'clear': self._clear_prompt,
      'set': lambda: self._set_prompt(args[1:]),
      'print': lambda: self._print_prompt(args[1:]),
      'delete': lambda: self._delete_prompt(args[1:])
    }
    
    handler = handlers.get(subcommand)
    if handler:
      return handler()
    return Result(success=False, message=f"Unknown prompt subcommand: {subcommand}\nUse {self.format_command('prompt')} to see available subcommands.")
  
  def _get_tool_params(self) -> Dict[str, Any]:
    """Get common parameters for cli tools."""
    return {
      'files_directory': self.settings.files_directory,
      'active_prompt_name': self.settings.active_prompt.prompt_name if self.settings.active_prompt else None,
      'default_prompt': self.settings.default_prompt,
    }
  
  def _show_usage(self) -> Result:
    """Show usage information and current active prompt."""
    prefix = self.get_help_prefix()
    active = self.settings.active_prompt
    
    lines = [f"\nActive prompt: {active.prompt_name}" if active else "\nNo active prompt"]
    lines.extend([
      "\nUsage:",
      f"  {prefix}prompt list              - List all available prompts",
      f"  {prefix}prompt set <name>        - Set the active prompt",
      f"  {prefix}prompt clear             - Clear the active prompt",
      f"  {prefix}prompt print [name]      - Print active prompt or specified prompt",
      f"  {prefix}prompt delete <name>     - Delete a stored prompt (requires confirmation)",
    ])
    return Result(success=True, data="\n".join(lines))
  
  def _list_prompts(self) -> Result:
    """List all available prompts."""
    return self.registry.run_command('cli.prompt_list', self._get_tool_params(), None)
  
  def _clear_prompt(self) -> Result:
    """Clear the active prompt."""
    if not self.settings.active_prompt:
      return Result(success=True, data="No active prompt to clear.")
    
    old_name = self.settings.active_prompt.prompt_name
    self.settings.active_prompt = None
    return Result(success=True, data=f"Cleared active prompt: {old_name}")
  
  def _set_prompt(self, args: List[str]) -> Result:
    """Set the active prompt."""
    if not args:
      return Result(success=False, message=f"Missing prompt name. Usage: {self.format_command('prompt set <name>')}")
    
    prompt_name = args[0]
    try:
      validated_name = Prompt.validate_prompt_name(prompt_name)
      file_repo = FileSystemStore(self.settings.files_directory)
      
      # Find and load the prompt
      prompts = file_repo.list_all(file_type='prompts')
      prompt_id = next((p.get('id') for p in prompts if p.get('prompt_name') == validated_name), None)
      
      if not prompt_id:
        return Result(success=False, message=f"Prompt '{validated_name}' not found.\nUse {self.format_command('prompt list')} to see available prompts.")
      
      prompt = file_repo.load(prompt_id, load_content=True)
      if not prompt:
        return Result(success=False, message=f"Error loading prompt '{validated_name}'.")
      
      self.settings.active_prompt = prompt
      output = f"\nActive prompt set to: {validated_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: {self.format_command(f'set default_prompt {validated_name}')}"
      return Result(success=True, data=output)
      
    except Exception as e:
      self.logger.error(f"Error setting prompt: {e}", exc_info=True)
      return Result(success=False, message=f"Error setting prompt '{prompt_name}': {str(e)}")
  
  def _print_prompt(self, args: List[str]) -> Result:
    """Print a prompt (active or specified)."""
    params = self._get_tool_params()
    if args:
      params['prompt_name'] = args[0]
    return self.registry.run_command('cli.prompt_print', params, None)
  
  def _delete_prompt(self, args: List[str]) -> Result:
    """Delete a stored prompt with confirmation."""
    if not args:
      return Result(success=False, message=f"Missing prompt name. Usage: {self.format_command('prompt delete <name>')}")
    
    try:
      validated_name = Prompt.validate_prompt_name(args[0])
      file_repo = FileSystemStore(self.settings.files_directory)
      
      # Find the prompt
      prompts = file_repo.list_all(file_type='prompts')
      prompt_id = next((p.get('id') for p in prompts if p.get('prompt_name') == validated_name), None)
      
      if not prompt_id:
        return Result(success=False, message=f"Prompt '{validated_name}' not found.")
      
      # Can't delete active prompt
      if self.settings.active_prompt and self.settings.active_prompt.prompt_name == validated_name:
        return Result(success=False, message=f"Cannot delete the active prompt '{validated_name}'.\nUse {self.format_command('prompt clear')} to clear the active prompt first.")
      
      # Confirmation
      print(f"\n⚠️  WARNING: You are about to delete prompt '{validated_name}'.")
      print("This action cannot be undone.")
      
      try:
        confirmation = input("\nType the prompt name to confirm deletion: ").strip()
        if confirmation != validated_name:
          return Result(success=True, message="Deletion cancelled. Name did not match.")
        
        if file_repo.delete(prompt_id):
          return Result(success=True, data=f"Successfully deleted prompt: {validated_name}")
        return Result(success=False, message=f"Failed to delete prompt: {validated_name}")
        
      except (KeyboardInterrupt, EOFError):
        print("\n\nDeletion cancelled.")
        return Result(success=True, message="Deletion cancelled by user")
      
    except Exception as e:
      self.logger.error(f"Error deleting prompt: {e}", exc_info=True)
      return Result(success=False, message=f"Error deleting prompt '{args[0]}': {str(e)}")

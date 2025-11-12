"""
Agent and Prompt command classes for the CLAIA CLI.

This module contains command classes for managing agents and prompts.
"""

import logging
from typing import List, Optional, Any

from claia.lib.results import Result
from claia.lib.data.models import Prompt
from claia.lib.data.repositories import FileSystemRepository
from .base import BaseCommand


logger = logging.getLogger(__name__)


# Constants for formatted output
AGENT_DIVIDER = "-" * 70
PROMPT_DIVIDER = "-" * 70


class AgentCommand(BaseCommand):
  """Command to manage active agent selection."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the agent command.
    
    Args:
        args: Optional list of arguments (empty, "list", or agent name)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result indicating success/failure
    """
    self.logger.debug("Agent command received")
    
    # If no args, show current active agent
    if not args:
      return self._show_current_agent()
    
    # If "list" argument, show available agents
    if args[0].lower() == "list":
      return self._list_agents()
    
    # Otherwise, switch to specified agent
    return self._switch_agent(args[0])
  
  def _show_current_agent(self) -> Result:
    """Show the current active agent and usage information."""
    current_agent = self.settings.active_agent or "None"
    default_agent = self.settings.default_agent or "None"
    
    output = f"\nCurrent active agent: {current_agent}"
    output += f"\nDefault agent (from settings): {default_agent}"
    output += "\n\nUsage:"
    
    if self._current_mode == 'interactive':
      output += "\n  :agent list          - List all available agents"
      output += "\n  :agent <agent_name>  - Switch to specified agent"
    else:
      output += "\n  --agent list          - List all available agents"
      output += "\n  --agent <agent_name>  - Switch to specified agent"
    
    return Result(success=True, data=output)
  
  def _list_agents(self) -> Result:
    """List all available agents."""
    try:
      agents_info = self.registry.manager.get_agents()
      
      if not agents_info:
        return Result(success=False, message="No agents available.")
      
      output_lines = []
      output_lines.append("\nAvailable Agents:")
      output_lines.append(AGENT_DIVIDER)
      
      for agent_info in agents_info:
        agent_name = agent_info.name
        description = getattr(agent_info, 'description', 'No description available')
        
        # Mark the current active agent
        marker = " (active)" if agent_name == self.settings.active_agent else ""
        marker += " (default)" if agent_name == self.settings.default_agent else ""
        
        output_lines.append(f"  • {agent_name}{marker}")
        output_lines.append(f"    {description}")
      
      output_lines.append("")
      output = "\n".join(output_lines)
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error listing agents: {str(e)}"
      self.logger.error(f"Error listing agents: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _switch_agent(self, agent_name: str) -> Result:
    """
    Switch to a specified agent.
    
    Args:
        agent_name: Name of the agent to switch to
    
    Returns:
        Result indicating success/failure
    """
    agent_name = agent_name.lower()
    
    try:
      agent_class = self.registry.get_agent_class(agent_name)
      
      if not agent_class:
        output = f"Unknown agent: {agent_name}\n"
        output += f"Use {self.format_command('agent list')} to see available agents."
        return Result(success=False, message=output)
      
      # Set the active agent (runtime only, not persisted)
      old_agent = self.settings.active_agent
      self.settings.active_agent = agent_name
      
      output = f"\nActive agent changed: {old_agent or 'None'} -> {agent_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: {self.format_command(f'set default_agent {agent_name}')}"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error switching to agent '{agent_name}': {str(e)}"
      self.logger.error(f"Error switching agent: {e}", exc_info=True)
      return Result(success=False, message=output)


class PromptCommand(BaseCommand):
  """Command to manage prompts (list, set, clear, delete, print)."""
  
  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    """
    Execute the prompt command.
    
    Args:
        args: List of arguments (subcommand and additional args)
        conversation: Optional conversation context (unused)
    
    Returns:
        Result indicating success/failure
    """
    self.logger.debug("Prompt command received")
    
    # If no args, show usage and current active prompt
    if not args:
      return self._show_usage()
    
    subcommand = args[0].lower()
    
    # Route to appropriate subcommand handler
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
    else:
      output = f"Unknown prompt subcommand: {subcommand}\n"
      output += f"Use {self.format_command('prompt')} to see available subcommands."
      return Result(success=False, message=output)
  
  def _show_usage(self) -> Result:
    """Show usage information and current active prompt."""
    output_lines = []
    
    if self.settings.active_prompt:
      output_lines.append(f"\nActive prompt: {self.settings.active_prompt.prompt_name}")
    else:
      output_lines.append("\nNo active prompt")
    
    output_lines.append("\nUsage:")
    prefix = self.get_help_prefix()
    
    output_lines.append(f"  {prefix}prompt list              - List all available prompts")
    output_lines.append(f"  {prefix}prompt set <name>        - Set the active prompt")
    output_lines.append(f"  {prefix}prompt clear             - Clear the active prompt")
    output_lines.append(f"  {prefix}prompt print [name]      - Print active prompt or specified prompt")
    output_lines.append(f"  {prefix}prompt delete <name>     - Delete a stored prompt (requires confirmation)")
    
    output = "\n".join(output_lines)
    return Result(success=True, data=output)
  
  def _list_prompts(self) -> Result:
    """List all available prompts."""
    try:
      file_repo = FileSystemRepository(self.settings.files_directory)
      prompts = file_repo.list_all(file_type='prompts')
      
      if not prompts:
        return Result(success=True, data="No prompts found.")
      
      output_lines = []
      output_lines.append("\nAvailable prompts:")
      output_lines.append(PROMPT_DIVIDER)
      
      for prompt_meta in prompts:
        prompt_name = prompt_meta.get('prompt_name', 'Unknown')
        
        # Mark the current active prompt
        marker = " (active)" if (self.settings.active_prompt and 
                                 self.settings.active_prompt.prompt_name == prompt_name) else ""
        marker += " (default)" if prompt_name == self.settings.default_prompt else ""
        
        output_lines.append(f"  • {prompt_name}{marker}")
      
      output_lines.append("")
      output = "\n".join(output_lines)
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error listing prompts: {str(e)}"
      self.logger.error(f"Error listing prompts: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _clear_prompt(self) -> Result:
    """Clear the active prompt."""
    if not self.settings.active_prompt:
      return Result(success=True, data="No active prompt to clear.")
    
    old_prompt_name = self.settings.active_prompt.prompt_name
    self.settings.active_prompt = None
    output = f"Cleared active prompt: {old_prompt_name}"
    return Result(success=True, data=output)
  
  def _set_prompt(self, args: List[str]) -> Result:
    """
    Set the active prompt.
    
    Args:
        args: List containing the prompt name
    
    Returns:
        Result indicating success/failure
    """
    if not args:
      output = f"Missing prompt name. Usage: {self.format_command('prompt set <name>')}"
      return Result(success=False, message=output)
    
    prompt_name = args[0]
    
    try:
      validated_name = Prompt.validate_prompt_name(prompt_name)
      file_repo = FileSystemRepository(self.settings.files_directory)
      
      # Find the prompt
      prompts = file_repo.list_all(file_type='prompts')
      prompt_id = None
      
      for prompt_meta in prompts:
        if prompt_meta.get('prompt_name') == validated_name:
          prompt_id = prompt_meta.get('id')
          break
      
      if not prompt_id:
        output = f"Prompt '{validated_name}' not found.\n"
        output += f"Use {self.format_command('prompt list')} to see available prompts."
        return Result(success=False, message=output)
      
      # Load the prompt
      prompt = file_repo.load(prompt_id, load_content=True)
      if not prompt:
        return Result(success=False, message=f"Error loading prompt '{validated_name}'.")
      
      self.settings.active_prompt = prompt
      output = f"\nActive prompt set to: {validated_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: {self.format_command(f'set default_prompt {validated_name}')}"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error setting prompt '{prompt_name}': {str(e)}"
      self.logger.error(f"Error setting prompt: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _print_prompt(self, args: List[str]) -> Result:
    """
    Print a prompt (active or specified).
    
    Args:
        args: Optional list containing prompt name
    
    Returns:
        Result with prompt content
    """
    try:
      file_repo = FileSystemRepository(self.settings.files_directory)
      
      # If prompt name specified, print that prompt
      if args:
        prompt = self._load_prompt_by_name(args[0], file_repo)
        if isinstance(prompt, Result):
          return prompt  # Error result
      else:
        # Print active prompt
        if not self.settings.active_prompt:
          output = f"No active prompt.\n"
          output += f"Use {self.format_command('prompt set <name>')} to set an active prompt."
          return Result(success=True, data=output)
        
        # Ensure content is loaded
        if not self.settings.active_prompt.has_content_loaded():
          self.settings.active_prompt = file_repo.load(
            self.settings.active_prompt.id, 
            load_content=True
          )
        
        prompt = self.settings.active_prompt
      
      output = f"\n{prompt.prompt_name}:"
      output += f"\n{PROMPT_DIVIDER}"
      output += f"\n{prompt.content}"
      output += f"\n{PROMPT_DIVIDER}\n"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error printing prompt: {str(e)}"
      self.logger.error(f"Error printing prompt: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _delete_prompt(self, args: List[str]) -> Result:
    """
    Delete a stored prompt.
    
    Args:
        args: List containing prompt name
    
    Returns:
        Result indicating success/failure
    """
    if not args:
      output = f"Missing prompt name. Usage: {self.format_command('prompt delete <name>')}"
      return Result(success=False, message=output)
    
    prompt_name = args[0]
    
    try:
      validated_name = Prompt.validate_prompt_name(prompt_name)
      file_repo = FileSystemRepository(self.settings.files_directory)
      
      # Find the prompt
      prompts = file_repo.list_all(file_type='prompts')
      prompt_id = None
      
      for prompt_meta in prompts:
        if prompt_meta.get('prompt_name') == validated_name:
          prompt_id = prompt_meta.get('id')
          break
      
      if not prompt_id:
        return Result(success=False, message=f"Prompt '{validated_name}' not found.")
      
      # Check if it's the active prompt
      if (self.settings.active_prompt and 
          self.settings.active_prompt.prompt_name == validated_name):
        output = f"Cannot delete the active prompt '{validated_name}'.\n"
        output += f"Use {self.format_command('prompt clear')} to clear the active prompt first."
        return Result(success=False, message=output)
      
      # Ask for confirmation
      print(f"\n⚠️  WARNING: You are about to delete prompt '{validated_name}'.")
      print("This action cannot be undone.")
      
      try:
        confirmation = input("\nType the prompt name to confirm deletion: ").strip()
        
        if confirmation != validated_name:
          return Result(success=True, message="Deletion cancelled. Name did not match.")
        
        # Delete the prompt
        if file_repo.delete(prompt_id):
          output = f"Successfully deleted prompt: {validated_name}"
          return Result(success=True, data=output)
        else:
          return Result(success=False, message=f"Failed to delete prompt: {validated_name}")
          
      except (KeyboardInterrupt, EOFError):
        print("\n\nDeletion cancelled.")
        return Result(success=True, message="Deletion cancelled by user")
      
    except Exception as e:
      output = f"Error deleting prompt '{prompt_name}': {str(e)}"
      self.logger.error(f"Error deleting prompt: {e}", exc_info=True)
      return Result(success=False, message=output)
  
  def _load_prompt_by_name(self, prompt_name: str, file_repo: FileSystemRepository):
    """
    Load a prompt by name from the repository.
    
    Args:
        prompt_name: Name of the prompt
        file_repo: File repository instance
    
    Returns:
        Prompt object or Result (error)
    """
    try:
      validated_name = Prompt.validate_prompt_name(prompt_name)
      
      # Find the prompt
      prompts = file_repo.list_all(file_type='prompts')
      prompt_id = None
      
      for prompt_meta in prompts:
        if prompt_meta.get('prompt_name') == validated_name:
          prompt_id = prompt_meta.get('id')
          break
      
      if not prompt_id:
        output = f"Prompt '{validated_name}' not found.\n"
        output += f"Use {self.format_command('prompt list')} to see available prompts."
        return Result(success=False, message=output)
      
      # Load the prompt with content
      prompt = file_repo.load(prompt_id, load_content=True)
      if not prompt:
        return Result(success=False, message=f"Error loading prompt '{validated_name}'.")
      
      return prompt
      
    except Exception as e:
      return Result(success=False, message=f"Error loading prompt: {str(e)}")


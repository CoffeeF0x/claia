"""
Entity command handlers for the CLAIA CLI.

This module contains handlers for entity-related commands like agent and prompt management.
"""

import logging
from typing import List

from claia.lib.results import Result
from claia.lib.data.models import Prompt
from claia.lib.data.repositories import FileSystemRepository


logger = logging.getLogger(__name__)


class EntityCommandsMixin:
  """Mixin class containing entity command handlers."""

  def _cmd_agent(self, args: List[str]) -> Result:
    """
    Handle agent command - manage active agent selection.

    Args:
        args: Optional list of arguments (empty, "list", or agent name)

    Returns:
        Result indicating success/failure
    """
    logger.debug("Agent command received")
    
    # If no args, show current active agent
    if not args:
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
    
    # If "list" argument, show available agents
    if args[0].lower() == "list":
      try:
        # Get all registered agents from the manager
        agents_info = self.registry.manager.get_agents()
        
        if not agents_info:
          output = "No agents available."
          return Result(success=False, message=output)
        
        output_lines = []
        output_lines.append("\nAvailable Agents:")
        output_lines.append("-" * 70)
        
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
        logger.error(f"Error listing agents: {e}", exc_info=True)
        return Result(success=False, message=output)
    
    # Otherwise, treat first arg as agent name to switch to
    agent_name = args[0].lower()
    
    # Validate that the agent exists
    try:
      agent_class = self.registry.get_agent_class(agent_name)
      
      if not agent_class:
        output = f"Unknown agent: {agent_name}"
        if self._current_mode == 'interactive':
          output += "\nUse ':agent list' to see available agents."
        else:
          output += "\nUse '--agent list' to see available agents."
        return Result(success=False, message=output)
      
      # Set the active agent (runtime only, not persisted)
      old_agent = self.settings.active_agent
      self.settings.active_agent = agent_name
      
      output = f"\nActive agent changed: {old_agent or 'None'} -> {agent_name}"
      output += "\n(Note: This change is for the current session only)"
      if self._current_mode == 'interactive':
        output += f"\nTo set as default for future sessions, use: :set default_agent {agent_name}"
      else:
        output += f"\nTo set as default for future sessions, use: --set default_agent {agent_name}"
      
      return Result(success=True, data=output)
      
    except Exception as e:
      output = f"Error switching to agent '{agent_name}': {str(e)}"
      logger.error(f"Error switching agent: {e}", exc_info=True)
      return Result(success=False, message=output)


  def _cmd_prompt(self, args: List[str]) -> Result:
    """
    Handle prompt command - manage prompts (list, set, clear, delete, print).

    Args:
        args: List of arguments (subcommand and additional args)

    Returns:
        Result indicating success/failure
    """
    logger.debug("Prompt command received")
    
    # If no args, show usage and current active prompt
    if not args:
      output_lines = []
      if self.settings.active_prompt:
        output_lines.append(f"\nActive prompt: {self.settings.active_prompt.prompt_name}")
      else:
        output_lines.append("\nNo active prompt")
      
      output_lines.append("\nUsage:")
      if self._current_mode == 'interactive':
        output_lines.append("  :prompt list              - List all available prompts")
        output_lines.append("  :prompt set <name>        - Set the active prompt")
        output_lines.append("  :prompt clear             - Clear the active prompt")
        output_lines.append("  :prompt print [name]      - Print active prompt or specified prompt")
        output_lines.append("  :prompt delete <name>     - Delete a stored prompt (requires confirmation)")
      else:
        output_lines.append("  --prompt list              - List all available prompts")
        output_lines.append("  --prompt set <name>        - Set the active prompt")
        output_lines.append("  --prompt clear             - Clear the active prompt")
        output_lines.append("  --prompt print [name]      - Print active prompt or specified prompt")
        output_lines.append("  --prompt delete <name>     - Delete a stored prompt (requires confirmation)")
      
      output = "\n".join(output_lines)
      return Result(success=True, data=output)
    
    subcommand = args[0].lower()
    
    # Create file repository for accessing prompts
    file_repo = FileSystemRepository(self.settings.files_directory)
    
    # Handle list subcommand
    if subcommand == "list":
      try:
        prompts = file_repo.list_all(file_type='prompts')
        
        if not prompts:
          output = "No prompts found."
          return Result(success=True, data=output)
        
        output_lines = []
        output_lines.append("\nAvailable prompts:")
        output_lines.append("-" * 70)
        
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
        logger.error(f"Error listing prompts: {e}", exc_info=True)
        return Result(success=False, message=output)
    
    # Handle clear subcommand
    elif subcommand == "clear":
      if not self.settings.active_prompt:
        output = "No active prompt to clear."
        return Result(success=True, data=output)
      
      old_prompt_name = self.settings.active_prompt.prompt_name
      self.settings.active_prompt = None
      output = f"Cleared active prompt: {old_prompt_name}"
      return Result(success=True, data=output)
    
    # Handle set subcommand
    elif subcommand == "set":
      if len(args) < 2:
        output = "Missing prompt name. Usage: "
        if self._current_mode == 'interactive':
          output += ":prompt set <name>"
        else:
          output += "--prompt set <name>"
        return Result(success=False, message=output)
      
      prompt_name = args[1]
      
      try:
        # Validate prompt name
        validated_name = Prompt.validate_prompt_name(prompt_name)
        
        # Load all prompts and find the matching one
        prompts = file_repo.list_all(file_type='prompts')
        prompt_id = None
        
        for prompt_meta in prompts:
          if prompt_meta.get('prompt_name') == validated_name:
            prompt_id = prompt_meta.get('id')
            break
        
        if not prompt_id:
          output = f"Prompt '{validated_name}' not found."
          if self._current_mode == 'interactive':
            output += "\nUse ':prompt list' to see available prompts."
          else:
            output += "\nUse '--prompt list' to see available prompts."
          return Result(success=False, message=output)
        
        # Load the prompt
        prompt = file_repo.load(prompt_id, load_content=True)
        if not prompt:
          output = f"Error loading prompt '{validated_name}'."
          return Result(success=False, message=output)
        
        self.settings.active_prompt = prompt
        output = f"\nActive prompt set to: {validated_name}"
        output += "\n(Note: This change is for the current session only)"
        if self._current_mode == 'interactive':
          output += f"\nTo set as default for future sessions, use: :set default_prompt {validated_name}"
        else:
          output += f"\nTo set as default for future sessions, use: --set default_prompt {validated_name}"
        
        return Result(success=True, data=output)
        
      except Exception as e:
        output = f"Error setting prompt '{prompt_name}': {str(e)}"
        logger.error(f"Error setting prompt: {e}", exc_info=True)
        return Result(success=False, message=output)
    
    # Handle print subcommand
    elif subcommand == "print":
      try:
        # If prompt name specified, print that prompt
        if len(args) >= 2:
          prompt_name = args[1]
          validated_name = Prompt.validate_prompt_name(prompt_name)
          
          # Load all prompts and find the matching one
          prompts = file_repo.list_all(file_type='prompts')
          prompt_id = None
          
          for prompt_meta in prompts:
            if prompt_meta.get('prompt_name') == validated_name:
              prompt_id = prompt_meta.get('id')
              break
          
          if not prompt_id:
            output = f"Prompt '{validated_name}' not found."
            if self._current_mode == 'interactive':
              output += "\nUse ':prompt list' to see available prompts."
            else:
              output += "\nUse '--prompt list' to see available prompts."
            return Result(success=False, message=output)
          
          # Load the prompt with content
          prompt = file_repo.load(prompt_id, load_content=True)
          if not prompt:
            output = f"Error loading prompt '{validated_name}'."
            return Result(success=False, message=output)
          
          output = f"\n{prompt.prompt_name}:"
          output += f"\n{'-' * 70}"
          output += f"\n{prompt.content}"
          output += f"\n{'-' * 70}\n"
          
        # Otherwise, print active prompt
        else:
          if not self.settings.active_prompt:
            output = "No active prompt."
            if self._current_mode == 'interactive':
              output += "\nUse ':prompt set <name>' to set an active prompt."
            else:
              output += "\nUse '--prompt set <name>' to set an active prompt."
            return Result(success=True, data=output)
          
          # Ensure content is loaded
          if not self.settings.active_prompt.has_content_loaded():
            self.settings.active_prompt = file_repo.load(
              self.settings.active_prompt.id, 
              load_content=True
            )
          
          output = f"\n{self.settings.active_prompt.prompt_name}:"
          output += f"\n{'-' * 70}"
          output += f"\n{self.settings.active_prompt.content}"
          output += f"\n{'-' * 70}\n"
        
        return Result(success=True, data=output)
        
      except Exception as e:
        output = f"Error printing prompt: {str(e)}"
        logger.error(f"Error printing prompt: {e}", exc_info=True)
        return Result(success=False, message=output)
    
    # Handle delete subcommand
    elif subcommand == "delete":
      if len(args) < 2:
        output = "Missing prompt name. Usage: "
        if self._current_mode == 'interactive':
          output += ":prompt delete <name>"
        else:
          output += "--prompt delete <name>"
        return Result(success=False, message=output)
      
      prompt_name = args[1]
      
      try:
        validated_name = Prompt.validate_prompt_name(prompt_name)
        
        # Load all prompts and find the matching one
        prompts = file_repo.list_all(file_type='prompts')
        prompt_id = None
        
        for prompt_meta in prompts:
          if prompt_meta.get('prompt_name') == validated_name:
            prompt_id = prompt_meta.get('id')
            break
        
        if not prompt_id:
          output = f"Prompt '{validated_name}' not found."
          return Result(success=False, message=output)
        
        # Check if it's the active prompt
        if (self.settings.active_prompt and 
            self.settings.active_prompt.prompt_name == validated_name):
          output = f"Cannot delete the active prompt '{validated_name}'."
          if self._current_mode == 'interactive':
            output += "\nUse ':prompt clear' to clear the active prompt first."
          else:
            output += "\nUse '--prompt clear' to clear the active prompt first."
          return Result(success=False, message=output)
        
        # Ask for confirmation
        print(f"\n⚠️  WARNING: You are about to delete prompt '{validated_name}'.")
        print("This action cannot be undone.")
        
        try:
          confirmation = input("\nType the prompt name to confirm deletion: ").strip()
          
          if confirmation != validated_name:
            output = "Deletion cancelled. Name did not match."
            return Result(success=True, message=output)
          
          # Delete the prompt
          if file_repo.delete(prompt_id):
            output = f"Successfully deleted prompt: {validated_name}"
            return Result(success=True, data=output)
          else:
            output = f"Failed to delete prompt: {validated_name}"
            return Result(success=False, message=output)
            
        except (KeyboardInterrupt, EOFError):
          print("\n\nDeletion cancelled.")
          return Result(success=True, message="Deletion cancelled by user")
        
      except Exception as e:
        output = f"Error deleting prompt '{prompt_name}': {str(e)}"
        logger.error(f"Error deleting prompt: {e}", exc_info=True)
        return Result(success=False, message=output)
    
    else:
      output = f"Unknown prompt subcommand: {subcommand}"
      if self._current_mode == 'interactive':
        output += "\nUse ':prompt' to see available subcommands."
      else:
        output += "\nUse '--prompt' to see available subcommands."
      return Result(success=False, message=output)


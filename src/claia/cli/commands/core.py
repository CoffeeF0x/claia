"""
Core command processing for the CLAIA CLI.

Handles command routing and execution for both CLI-style (--flag) and
interactive (:command) modes.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Type

from claia.core.results import Result
from claia.framework.registry import Registry
from .specs import COMMAND_SPECS, CommandPriority, generate_cli_alias
from .base import BaseCommand
from .system import QuitCommand, HelpCommand, VersionCommand
from .get_set import GetCommand, SetCommand, ResetCommand
from .setup import SetupCommand
from .agent import AgentCommand, PromptCommand
from .tool import ToolCommand
from .conversation import ConversationCommand
from .model import ModelCommand
from .query import QueryCommand
from .file import ExportFileCommand, FileCommand, ImportFileCommand


logger = logging.getLogger(__name__)


# Command registry mapping command names to their classes
COMMAND_REGISTRY: Dict[str, Type[BaseCommand]] = {
  'quit': QuitCommand,
  'exit': QuitCommand,
  'help': HelpCommand,
  'version': VersionCommand,
  'get': GetCommand,
  'set': SetCommand,
  'reset': ResetCommand,
  'setup': SetupCommand,
  'agent': AgentCommand,
  'prompt': PromptCommand,
  'conversation': ConversationCommand,
  'model': ModelCommand,
  'query': QueryCommand,
  'tool': ToolCommand,
  'file': FileCommand,
  'import': ImportFileCommand,
  'export': ExportFileCommand,
}


class Commands:
  """Processes and executes commands for CLI and interactive modes."""
  
  def __init__(self, registry: Registry, settings: Any):
    self.registry = registry
    self.settings = settings
    self._current_mode = 'interactive'
    
    # Maps alias -> (command_class, help_text, needs_args, needs_conversation, priority)
    self._cli_command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool, CommandPriority]] = {}
    self._interactive_command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool, CommandPriority]] = {}
    self._build_command_maps()
  
  def _build_command_maps(self) -> None:
    """Build command lookup dictionaries from COMMAND_SPECS."""
    for aliases, cmd_name, help_text, needs_args, needs_conversation, priority in COMMAND_SPECS:
      command_class = COMMAND_REGISTRY.get(cmd_name)
      if not command_class:
        logger.warning(f"No command class found for '{cmd_name}'")
        continue
      
      for alias in aliases:
        entry = (command_class, help_text, needs_args, needs_conversation, priority)
        self._interactive_command_map[alias.lower()] = entry
        self._cli_command_map[generate_cli_alias(alias)] = entry
  
  def run(self, tokens: List[str], conversation: Optional[Any] = None, 
          is_interactive: bool = False) -> Result:
    """
    Process and execute a command from tokens.
    
    In CLI mode, supports multiple commands delimited by dash-prefixed tokens.
    In interactive mode, processes one command per call.
    """
    if not tokens:
      return Result(success=True)
    
    self._current_mode = 'interactive' if is_interactive else 'cli'
    
    # Handle multiple CLI commands
    if not is_interactive:
      command_groups = self._split_cli_commands(tokens)
      if len(command_groups) > 1:
        return self._execute_multiple_commands(command_groups, conversation)
    
    cmd, args = tokens[0], tokens[1:]
    
    # Try CLI-style flags first (--flag or -f)
    if not is_interactive and cmd in self._cli_command_map:
      return self._execute_command(cmd, args, conversation, self._cli_command_map)
    
    # Try interactive-style commands
    cmd_lower = cmd.lower()
    if cmd_lower in self._interactive_command_map:
      return self._execute_command(cmd_lower, args, conversation, self._interactive_command_map)
    
    # Unknown command
    prefix = ':' if is_interactive else '--'
    output = f"Unknown command: {cmd}\n"
    output += f"Use '{prefix}help' to see available commands or '{prefix}tool' to see available tools."
    return Result(success=False, message=output)
  
  def _execute_command(self, cmd: str, args: List[str], conversation: Optional[Any],
                      command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool, CommandPriority]]) -> Result:
    """Execute a command using the provided command map."""
    command_class, _, needs_args, needs_conversation, _ = command_map[cmd]
    
    # Check for missing required args (specific to SetCommand)
    if needs_args and command_class == SetCommand and not args:
      return Result(success=False, message="No setting provided. Usage: set <key> <value> or key=value")
    
    # Instantiate command
    if command_class == HelpCommand:
      instance = command_class(self.registry, self.settings, self._current_mode, command_specs=COMMAND_SPECS)
    else:
      instance = command_class(self.registry, self.settings, self._current_mode)
    
    try:
      return instance.execute(args, conversation) if needs_conversation else instance.execute(args)
    except Exception as e:
      logger.error(f"Error executing command '{cmd}': {e}", exc_info=True)
      return Result(success=False, message=f"Error executing command: {str(e)}")
  
  def _split_cli_commands(self, tokens: List[str]) -> List[List[str]]:
    """Split CLI tokens into command groups based on dash prefixes."""
    if not tokens:
      return []
    
    groups, current = [], []
    for token in tokens:
      if token in self._cli_command_map and current:
        groups.append(current)
        current = [token]
      else:
        current.append(token)
    
    if current:
      groups.append(current)
    return groups
  
  def _execute_multiple_commands(self, command_groups: List[List[str]], 
                                 conversation: Optional[Any]) -> Result:
    """Execute multiple command groups with priority ordering."""
    groups = [g for g in command_groups if g]
    if not groups:
      return Result(success=True)
    
    # Resolve priorities
    prioritized = []
    for group in groups:
      cmd = group[0]
      if cmd not in self._cli_command_map:
        output = f"Unknown command: {cmd}\n"
        output += "Use '--help' to see available commands or '--tool' to see available tools."
        return Result(success=False, message=output)
      
      _, _, _, _, priority = self._cli_command_map[cmd]
      prioritized.append((priority, group))
    
    prioritized.sort(key=lambda x: x[0])
    
    # IMMEDIATE commands execute exclusively
    if prioritized[0][0] == CommandPriority.IMMEDIATE:
      group = prioritized[0][1]
      return self._execute_command(group[0], group[1:], conversation, self._cli_command_map)
    
    # Execute in priority order
    output_parts = []
    for priority, group in prioritized:
      cmd, args = group[0], group[1:]
      result = self._execute_command(cmd, args, conversation, self._cli_command_map)
      
      if not result.is_success() or result.is_exit():
        if output_parts:
          combined = '\n'.join(output_parts)
          if result.get_data():
            combined += '\n' + str(result.get_data())
          return Result(
            success=result.is_success(),
            message=result.get_message(),
            data=combined if combined else result.get_data(),
            exit_code=result.get_exit_code()
          )
        return result
      
      if result.get_data() is not None:
        output_parts.append(str(result.get_data()))
    
    return Result(success=True, data='\n'.join(output_parts)) if output_parts else Result(success=True)

"""
Core command processing and registry for the CLAIA application.

This module handles command routing, registration, and execution for both CLI-style
commands (with flags like -q, --quit) and interactive commands (with simple prefixes 
like :q, :quit).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Type

from claia.lib.results import Result
from claia.registry import Registry
from .specs import COMMAND_SPECS, generate_cli_alias
from .base import BaseCommand
from .system import QuitCommand, HelpCommand, VersionCommand
from .get_set import GetCommand, SetCommand
from .setup import SetupCommand
from .agent import AgentCommand, PromptCommand
from .tool import ToolCommand
from .conversation import ConversationCommand
from .model import ModelCommand
from .query import QueryCommand


logger = logging.getLogger(__name__)


# Command registry mapping command names to their classes
COMMAND_REGISTRY: Dict[str, Type[BaseCommand]] = {
  'quit': QuitCommand,
  'exit': QuitCommand,
  'help': HelpCommand,
  'version': VersionCommand,
  'get': GetCommand,
  'set': SetCommand,
  'setup': SetupCommand,
  'agent': AgentCommand,
  'prompt': PromptCommand,
  'conversation': ConversationCommand,
  'model': ModelCommand,
  'query': QueryCommand,
  'tool': ToolCommand,
}


class Commands:
  """
  Processes and executes commands for the CLAIA application.
  Handles both CLI-style flags and interactive-style commands.
  """
  
  def __init__(self, registry: Registry, settings: Any):
    """
    Initialize the Commands processor.
    
    Args:
        registry: The unified registry for tools, models, and agents
        settings: The settings object containing configuration
    """
    self.registry = registry
    self.settings = settings
    self._current_mode = 'interactive'  # Default to interactive mode
    
    # Build command lookup dictionaries from COMMAND_SPECS
    # Maps alias -> (command_class, help_text, needs_args, needs_conversation)
    self._cli_command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool]] = {}
    self._interactive_command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool]] = {}
    
    self._build_command_maps()
    
    logger.debug("Commands processor initialized")
  
  def _build_command_maps(self) -> None:
    """Build command lookup dictionaries from COMMAND_SPECS."""
    for aliases, handler_name, help_text, needs_args, needs_conversation in COMMAND_SPECS:
      # Extract the command name from the handler method name (e.g., '_cmd_quit' -> 'quit')
      cmd_name = handler_name.replace('_cmd_', '')
      
      # Get the command class from the registry
      command_class = COMMAND_REGISTRY.get(cmd_name)
      
      if not command_class:
        logger.warning(f"No command class found for '{cmd_name}' (handler: {handler_name})")
        continue
      
      for alias in aliases:
        # Map interactive alias (no prefix)
        self._interactive_command_map[alias.lower()] = (
          command_class, help_text, needs_args, needs_conversation
        )
        
        # Map CLI alias (with - or -- prefix)
        cli_alias = generate_cli_alias(alias)
        self._cli_command_map[cli_alias] = (
          command_class, help_text, needs_args, needs_conversation
        )
  
  def run(self, tokens: List[str], conversation: Optional[Any] = None, 
          is_interactive: bool = False) -> Result:
    """
    Process and execute a command from a list of tokens.
    
    Args:
        tokens: List of command tokens (e.g., ['--quit'] or ['q'] or ['tool', 'arg1', 'arg2'])
        conversation: Optional conversation context for tool execution
        is_interactive: Whether this is an interactive command (affects parsing)
    
    Returns:
        Result object indicating success/failure and any output data
    """
    if not tokens:
      return Result(success=True)
    
    # Store mode for use by command handlers
    self._current_mode = 'interactive' if is_interactive else 'cli'
    
    # Get the first token as the command
    cmd = tokens[0]
    args = tokens[1:]
    
    # Handle CLI-style flags (--flag or -f) when not in interactive mode
    if not is_interactive:
      result = self._process_cli_flag(cmd, args, conversation)
      if result:
        return result
    
    # Handle interactive-style commands
    result = self._process_interactive_command(cmd, args, conversation)
    if result:
      return result
    
    # If no built-in command matched, return error
    output = f"Unknown command: {cmd}"
    if is_interactive:
      output += "\nUse ':help' to see available commands or ':tool' to see available tools."
    else:
      output += "\nUse '--help' to see available commands or '--tool' to see available tools."
    return Result(success=False, message=output)
  
  def _process_cli_flag(self, cmd: str, args: List[str], 
                       conversation: Optional[Any]) -> Optional[Result]:
    """
    Process CLI-style flag commands (--flag or -f format).
    
    Args:
        cmd: The command/flag string
        args: Remaining arguments
        conversation: Optional conversation context
    
    Returns:
        Result if command was processed, None if not recognized
    """
    if cmd in self._cli_command_map:
      return self._execute_command(cmd, args, conversation, self._cli_command_map)
    return None
  
  def _process_interactive_command(self, cmd: str, args: List[str], 
                                   conversation: Optional[Any]) -> Optional[Result]:
    """
    Process interactive-style commands (simple word format like 'quit', 'help').
    
    Args:
        cmd: The command string
        args: Remaining arguments
        conversation: Optional conversation context
    
    Returns:
        Result if command was processed, None if not recognized
    """
    cmd_lower = cmd.lower()
    if cmd_lower in self._interactive_command_map:
      return self._execute_command(cmd_lower, args, conversation, self._interactive_command_map)
    return None
  
  def _execute_command(self, cmd: str, args: List[str], conversation: Optional[Any],
                      command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool]]) -> Result:
    """
    Execute a command using the provided command map.
    
    Args:
        cmd: The command string to execute
        args: Arguments for the command
        conversation: Optional conversation context
        command_map: The command map to look up the handler
    
    Returns:
        Result from command execution
    """
    command_class, _, needs_args, needs_conversation = command_map[cmd]
    
    # Check if command requires args but none provided (specific check for 'set')
    if needs_args and command_class == SetCommand and not args:
      return Result(success=False, message="No setting provided. Usage: set <key> <value> or key=value")
    
    # Instantiate the command with appropriate context
    # Special handling for HelpCommand which needs command_specs
    if command_class == HelpCommand:
      command_instance = command_class(
        self.registry, 
        self.settings, 
        self._current_mode,
        command_specs=COMMAND_SPECS
      )
    else:
      command_instance = command_class(self.registry, self.settings, self._current_mode)
    
    # Execute the command
    try:
      if needs_conversation:
        result = command_instance.execute(args, conversation)
      else:
        result = command_instance.execute(args)
      return result
    except Exception as e:
      logger.error(f"Error executing command '{cmd}': {e}", exc_info=True)
      return Result(success=False, message=f"Error executing command: {str(e)}")


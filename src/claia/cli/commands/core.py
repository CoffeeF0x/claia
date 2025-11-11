"""
Core command processing for the CLAIA application.

This module handles both CLI-style commands (with flags like -q, --quit) and interactive
commands (with simple prefixes like :q, :quit), routing them to appropriate handlers
or the registry's tool system.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple

from claia.lib.results import Result
from claia.registry import Registry
from .specs import COMMAND_SPECS, generate_cli_alias
from .system_handlers import SystemCommandsMixin
from .config_handlers import ConfigCommandsMixin
from .tool_handlers import ToolCommandsMixin
from .entity_handlers import EntityCommandsMixin


logger = logging.getLogger(__name__)


class Commands(SystemCommandsMixin, ConfigCommandsMixin, ToolCommandsMixin, EntityCommandsMixin):
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
    # Maps alias -> (handler_name, help_text, needs_args, needs_conversation)
    self._cli_command_map: Dict[str, Tuple[str, str, bool, bool]] = {}
    self._interactive_command_map: Dict[str, Tuple[str, str, bool, bool]] = {}
    
    for aliases, handler_name, help_text, needs_args, needs_conversation in COMMAND_SPECS:
      for alias in aliases:
        # Map interactive alias (no prefix)
        self._interactive_command_map[alias.lower()] = (handler_name, help_text, needs_args, needs_conversation)
        
        # Map CLI alias (with - or -- prefix)
        cli_alias = generate_cli_alias(alias)
        self._cli_command_map[cli_alias] = (handler_name, help_text, needs_args, needs_conversation)
    
    logger.debug("Commands processor initialized")


  def run(self, tokens: List[str], conversation: Optional[Any] = None, is_interactive: bool = False) -> Result:
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


  def _process_cli_flag(self, cmd: str, args: List[str], conversation: Optional[Any]) -> Optional[Result]:
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


  def _process_interactive_command(self, cmd: str, args: List[str], conversation: Optional[Any]) -> Optional[Result]:
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
                      command_map: Dict[str, Tuple[str, str, bool, bool]]) -> Result:
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
    handler_name, _, needs_args, needs_conversation = command_map[cmd]
    handler = getattr(self, handler_name)
    
    # Check if command requires args but none provided
    if needs_args and handler_name == '_cmd_set' and not args:
      return Result(success=False, message="No setting provided. Usage: set <key> <value> or key=value")
    
    # Call handler with appropriate arguments
    if needs_conversation and needs_args:
      return handler(args, conversation)
    elif needs_args:
      return handler(args)
    else:
      return handler()


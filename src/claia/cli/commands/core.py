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
from .specs import COMMAND_SPECS, CommandPriority, generate_cli_alias
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
    # Maps alias -> (command_class, help_text, needs_args, needs_conversation, priority)
    self._cli_command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool, CommandPriority]] = {}
    self._interactive_command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool, CommandPriority]] = {}
    
    self._build_command_maps()
    
    logger.debug("Commands processor initialized")
  
  def _build_command_maps(self) -> None:
    """Build command lookup dictionaries from COMMAND_SPECS."""
    for aliases, handler_name, help_text, needs_args, needs_conversation, priority in COMMAND_SPECS:
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
          command_class, help_text, needs_args, needs_conversation, priority
        )
        
        # Map CLI alias (with - or -- prefix)
        cli_alias = generate_cli_alias(alias)
        self._cli_command_map[cli_alias] = (
          command_class, help_text, needs_args, needs_conversation, priority
        )
  
  def run(self, tokens: List[str], conversation: Optional[Any] = None, 
          is_interactive: bool = False) -> Result:
    """
    Process and execute a command from a list of tokens.
    
    In CLI mode, supports multiple commands in a single call. Commands are delimited
    by dash-prefixed tokens (e.g., '--set model gpt-4 --query "What is AI?"').
    
    In interactive mode, only one command is processed per call.
    
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
    
    # In CLI mode, check for multiple commands (dash-prefixed tokens)
    if not is_interactive:
      command_groups = self._split_cli_commands(tokens)
      if len(command_groups) > 1:
        return self._execute_multiple_commands(command_groups, conversation)
    
    # Single command execution (interactive mode or single CLI command)
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
                      command_map: Dict[str, Tuple[Type[BaseCommand], str, bool, bool, CommandPriority]]) -> Result:
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
    command_class, _, needs_args, needs_conversation, _ = command_map[cmd]
    
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
  
  def _split_cli_commands(self, tokens: List[str]) -> List[List[str]]:
    """
    Split CLI tokens into separate command groups based on dash prefixes.
    
    A token starting with '-' or '--' indicates the start of a new command.
    All tokens following it (until the next dash-prefixed token) are arguments.
    
    Args:
        tokens: List of all tokens from the command line
    
    Returns:
        List of command groups, where each group is [command, arg1, arg2, ...]
    
    Example:
        ['--set', 'model', 'gpt-4', '--query', 'What is AI?']
        -> [['--set', 'model', 'gpt-4'], ['--query', 'What is AI?']]
    """
    if not tokens:
      return []
    
    command_groups = []
    current_group = []
    
    for token in tokens:
      # Check if this token starts a new command (starts with dash)
      if token.startswith('-') and current_group:
        # Save the previous command group
        command_groups.append(current_group)
        current_group = [token]
      else:
        # Add to current group
        current_group.append(token)
    
    # Don't forget the last group
    if current_group:
      command_groups.append(current_group)
    
    return command_groups
  
  def _execute_multiple_commands(self, command_groups: List[List[str]], 
                                 conversation: Optional[Any]) -> Result:
    """
    Execute multiple command groups with priority ordering and output compilation.
    
    Priority ordering ensures:
    - IMMEDIATE commands (help, version, quit) execute exclusively
    - CONFIG commands (set, get, etc.) execute before ACTION commands
    - Query and tool commands execute last after settings are applied
    
    Args:
        command_groups: List of command groups to execute
        conversation: Optional conversation context
    
    Returns:
        Result with compiled output from all commands, or first error/exit
    """
    # NOTE: The "if not group" check is safe because _split_cli_commands always
    # includes at least the command token. This would only trigger if we had
    # an empty list somehow, but we keep it for defensive programming.
    filtered_groups = [g for g in command_groups if g]
    
    if not filtered_groups:
      return Result(success=True)
    
    # Resolve priorities for all commands
    prioritized_groups = []
    for group in filtered_groups:
      cmd = group[0]
      if cmd not in self._cli_command_map:
        # Unknown command - return error immediately
        output = f"Unknown command: {cmd}"
        output += "\nUse '--help' to see available commands or '--tool' to see available tools."
        return Result(success=False, message=output)
      
      # Get priority from command map
      _, _, _, _, priority = self._cli_command_map[cmd]
      prioritized_groups.append((priority, group))
    
    # Sort by priority (lower values first)
    prioritized_groups.sort(key=lambda x: x[0])
    
    # Check if any IMMEDIATE commands exist - if so, execute only the first one
    if prioritized_groups[0][0] == CommandPriority.IMMEDIATE:
      priority, group = prioritized_groups[0]
      logger.debug(f"Executing IMMEDIATE command exclusively: {group[0]}")
      cmd = group[0]
      args = group[1:] if len(group) > 1 else []
      return self._process_cli_flag(cmd, args, conversation)
    
    # Execute commands in priority order and compile output
    output_parts = []
    last_result = Result(success=True)
    
    for i, (priority, group) in enumerate(prioritized_groups):
      cmd = group[0]
      args = group[1:] if len(group) > 1 else []
      
      logger.debug(f"Executing command {i+1}/{len(prioritized_groups)} "
                  f"(priority={priority}): {cmd}")
      
      result = self._process_cli_flag(cmd, args, conversation)
      
      if not result:
        # This shouldn't happen since we checked earlier, but be defensive
        output = f"Unknown command: {cmd}"
        output += "\nUse '--help' to see available commands or '--tool' to see available tools."
        return Result(success=False, message=output)
      
      # If command failed or requested exit, return immediately
      if not result.is_success() or result.is_exit():
        logger.debug(f"Stopping command chain at {i+1}/{len(prioritized_groups)}")
        # If we have collected output, prepend it to the error/exit result
        if output_parts:
          combined_output = '\n'.join(output_parts)
          if result.get_data():
            combined_output += '\n' + str(result.get_data())
          # Return a new result with combined data
          return Result(
            success=result.is_success(),
            message=result.get_message(),
            data=combined_output if combined_output else result.get_data(),
            exit_code=result.get_exit_code()
          )
        return result
      
      # Collect output from successful command
      data = result.get_data()
      if data is not None:
        output_parts.append(str(data))
      
      last_result = result
    
    # Return final result with all compiled output
    if output_parts:
      combined_output = '\n'.join(output_parts)
      return Result(success=True, data=combined_output)
    
    return last_result


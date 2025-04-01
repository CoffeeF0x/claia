from abc import ABC
from functools import wraps
from typing import List, Dict, Any, Callable, Optional, Union
import logging

# Internal Dependencies
from results import Result
from settings import Settings



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                          COMMAND DECORATOR                           #
########################################################################
def command(
    path: List[str] = None,
    description: str = None,
    help_text: str = None,
    parameters: Dict[str, Any] = None,
    returns: Dict[str, Any] = None,
    ai_callable: bool = True,
    aliases: List[Union[str, List[str]]] = None,
    top_level: bool = False
):
  """
  Decorator for command methods. Registers a method as a command with metadata.

  Args:
    path: The command path (e.g., ["set"] or ["vllm", "zone"]). If None, uses the function name.
    description: Brief description of what the command does (used for AI function calling)
    help_text: Detailed help text shown to users (used for CLI help)
    parameters: JSON Schema for command parameters
    returns: JSON Schema for return value
    ai_callable: Whether this command can be called by AI via function calling
    aliases: List of alternative paths for the same command (e.g., [["c"], ["cls"]] for clear)
    top_level: Whether this command should be registered at the top level (without class prefix)
  """
  # Validate no underscores in path
  if path:
    for part in path:
      if '_' in part:
        raise ValueError(f"Command path part '{part}' contains underscores, which are not allowed")

  # Validate no underscores in aliases
  if aliases:
    for alias in aliases:
      if isinstance(alias, str):
        if '_' in alias:
          raise ValueError(f"Command alias '{alias}' contains underscores, which are not allowed")
      elif isinstance(alias, list):
        for part in alias:
          if '_' in part:
            raise ValueError(f"Command alias part '{part}' contains underscores, which are not allowed")

  def decorator(func):
    # If path is None, use the function name as the path
    func._command_path = path or [func.__name__.lower()]
    func._command_description = description or func.__doc__ or ""
    func._command_help_text = help_text or func._command_description
    func._command_parameters = parameters or {}
    func._command_returns = returns or {"type": "string"}
    func._command_ai_callable = ai_callable
    func._command_aliases = aliases or []
    func._command_top_level = top_level

    @wraps(func)
    def wrapper(*args, **kwargs):
      return func(*args, **kwargs)
    return wrapper
  return decorator



########################################################################
#                              BASE CLASS                              #
########################################################################
class Command(ABC):
  def __init__(self):
    """Initialize command and build the command map from decorated methods"""
    self.command_map = {}
    self.top_level_commands = {}  # Store top-level commands
    self._build_command_map()

  def _build_command_map(self):
    """Build command map from methods decorated with @command"""
    try:
      self.command_map = {}
      self.top_level_commands = {}  # Store top-level commands

      # Get class name without "Command" suffix to use as module prefix
      module_prefix = self.__class__.__name__.replace("Command", "").lower()

      # For modules, use the module name instead
      if hasattr(self, '_module_name'):
        module_prefix = f"modules_{self._module_name}"

      for attr_name in dir(self):
        if attr_name.startswith('_'):
          continue

        try:
          attr = getattr(self, attr_name)
          if callable(attr) and hasattr(attr, '_command_path'):
            # Build the command key from the path
            cmd_path = attr._command_path
            cmd_key = '_'.join(cmd_path)

            # Register the command with the module prefix
            full_key = f"{module_prefix}_{cmd_key}"
            self.command_map[full_key] = {
              "function": attr,
              "description": attr._command_description,
              "help_text": attr._command_help_text,
              "parameters": attr._command_parameters,
              "returns": attr._command_returns,
              "ai_callable": attr._command_ai_callable,
              "path": cmd_path
            }

            # Also register command aliases
            for alias_path in attr._command_aliases:
              # Convert string to list if needed
              if isinstance(alias_path, str):
                alias_key = alias_path
                self.command_map[f"{module_prefix}_{alias_key}"] = self.command_map[full_key]
              elif isinstance(alias_path, list):
                alias_key = '_'.join(alias_path)
                self.command_map[f"{module_prefix}_{alias_key}"] = self.command_map[full_key]

            # Mark as top level if needed
            if attr._command_top_level:
              # For top level commands, use the last part of the path as the command name
              cmd_name = cmd_path[-1]
              self.top_level_commands[cmd_name] = attr

              # Also register any string aliases as top-level commands
              for alias_path in attr._command_aliases:
                if isinstance(alias_path, str):
                  self.top_level_commands[alias_path] = attr
                elif isinstance(alias_path, list) and len(alias_path) == 1:
                  self.top_level_commands[alias_path[0]] = attr

        except Exception as e:
          logger.error(f"Error processing attribute {attr_name}: {str(e)}")
    except Exception as e:
      logger.error(f"Error building command map: {str(e)}")
      # Initialize empty maps to prevent further errors
      self.command_map = {}
      self.top_level_commands = {}

  def execute(self, commands: list[str], settings: Settings) -> Result:
    """Execute a command by looking it up in the command map and calling the function"""
    result = Result()

    # Parse arguments and flags
    args = []
    kwargs = {}

    # Handle top-level commands
    if len(commands) == 1 and commands[0] in self.top_level_commands:
      func = self.top_level_commands[commands[0]]
      try:
        func_result = func(settings, *args, **kwargs)
        if isinstance(func_result, Result):
          result = func_result
        return result
      except Exception as e:
        result.fail(f"Error executing top-level command: {str(e)}")
        return result

    # Handle module commands
    elif len(commands) > 1:
      # Convert space-separated command to underscore format for lookup
      module_prefix = self.__class__.__name__.replace("Command", "").lower()
      if hasattr(self, '_module_name'):
        module_prefix = f"modules_{self._module_name}"

      # First try exact command path
      cmd_key = '_'.join(commands[1:])  # Skip the module name at position 0
      full_key = f"{module_prefix}_{cmd_key}"

      if full_key in self.command_map:
        func = self.command_map[full_key]["function"]
        try:
          func_result = func(settings, *args, **kwargs)
          if isinstance(func_result, Result):
            result = func_result
          return result
        except Exception as e:
          result.fail(f"Error executing command: {str(e)}")
          return result

      # Otherwise, process arguments
      remaining_parts = commands[1:]
      for i in range(len(remaining_parts)):
        # Try each combination of command parts
        cmd_key = '_'.join(remaining_parts[:i+1])
        full_key = f"{module_prefix}_{cmd_key}"

        if full_key in self.command_map:
          func = self.command_map[full_key]["function"]

          # Any remaining parts are treated as arguments
          for part in remaining_parts[i+1:]:
            if part.startswith("--"):
              # Handle flag
              flag_name = part[2:]
              kwargs[flag_name] = True
            elif "=" in part:
              # Handle key=value
              key, value = part.split("=", 1)
              kwargs[key] = value
            else:
              # Positional argument
              args.append(part)

          try:
            func_result = func(settings, *args, **kwargs)
            if isinstance(func_result, Result):
              result = func_result
            return result
          except Exception as e:
            result.fail(f"Error executing command: {str(e)}")
            return result

    # Command not found or incomplete - show help for this module
    result.fail("Command incomplete or not recognized")
    self.help()
    return result

  def unrecognizedCommand(self) -> None:
    """Display message for unrecognized command and show available commands"""
    print("Command incomplete or not recognized")
    print("\nAvailable commands in this module:")
    self.help()

  def help(self) -> None:
    """Display help for this command, using help_text from decorators"""
    print(f"Here are the available {self.__class__.__name__.replace('Command', '').lower()} commands:")

    # Group commands by their prefix paths
    command_groups = {}

    for full_key, cmd_data in self.command_map.items():
      # Skip redundant entries due to aliases
      path_str = ' '.join(cmd_data["path"])
      if path_str not in command_groups:
        command_groups[path_str] = {
          "help_text": cmd_data["help_text"],
          "aliases": []
        }

    # Display commands
    for path_str, group in sorted(command_groups.items()):
      aliases = " ".join(group["aliases"]) if group["aliases"] else ""
      alias_display = f" (aliases: {aliases})" if aliases else ""
      print(f"  {path_str}{alias_display}")
      print(f"    - {group['help_text']}")

  def get_function_definitions(self) -> List[Dict[str, Any]]:
    """Get AI-callable function definitions for function calling"""
    definitions = []

    for full_key, cmd_data in self.command_map.items():
      if cmd_data.get("ai_callable", False):
        # Create function definition compatible with OpenAI format
        definition = {
          "name": full_key,
          "description": cmd_data["description"],
          "parameters": cmd_data["parameters"],
          "returns": cmd_data["returns"]
        }
        definitions.append(definition)

    return definitions

  def get_top_level_commands(self) -> Dict[str, Callable]:
    """Get commands that should be registered at the top level"""
    return self.top_level_commands
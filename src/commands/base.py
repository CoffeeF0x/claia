from abc import ABC
from functools import wraps
from typing import List, Dict, Any, Callable, Optional, Union
import logging

# Internal Dependencies
from errors import Result
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
    """Initialize command and build the function tree from decorated methods"""
    self.function_tree = {}
    self.top_level_commands = {}  # Store top-level commands
    self._build_function_tree()

  def _build_function_tree(self):
    """Build command tree from methods decorated with @command"""
    try:
      self.function_tree = {}
      self.top_level_commands = {}  # Store top-level commands

      for attr_name in dir(self):
        if attr_name.startswith('_'):
          continue

        try:
          attr = getattr(self, attr_name)
          if callable(attr) and hasattr(attr, '_command_path'):
            # Validate command path - no underscores allowed
            for path_part in attr._command_path:
              if '_' in path_part:
                raise ValueError(f"Command path part '{path_part}' contains underscores, which are not allowed")

            # Method has command metadata from decorator
            self._register_command_path(attr._command_path, attr)

            # Mark as top level if needed
            if attr._command_top_level:
              # For top level commands, use the last part of the path as the command name
              cmd_name = attr._command_path[-1]
              self.top_level_commands[cmd_name] = attr

              # Also register any string aliases as top-level commands
              for alias_path in attr._command_aliases:
                if isinstance(alias_path, str):
                  # Validate alias - no underscores allowed
                  if '_' in alias_path:
                    raise ValueError(f"Command alias '{alias_path}' contains underscores, which are not allowed")
                  self.top_level_commands[alias_path] = attr
                elif isinstance(alias_path, list) and len(alias_path) == 1:
                  # Validate alias - no underscores allowed
                  if '_' in alias_path[0]:
                    raise ValueError(f"Command alias '{alias_path[0]}' contains underscores, which are not allowed")
                  self.top_level_commands[alias_path[0]] = attr

            # Register any aliases in the function tree
            for alias_path in attr._command_aliases:
              # Convert string to list if needed
              if isinstance(alias_path, str):
                alias_path = [alias_path]

              # Validate alias path - no underscores allowed
              for path_part in alias_path:
                if '_' in path_part:
                  raise ValueError(f"Command alias path part '{path_part}' contains underscores, which are not allowed")

              self._register_command_path(alias_path, attr)
        except Exception as e:
          print(f"Error processing attribute {attr_name}: {str(e)}")
    except Exception as e:
      print(f"Error building function tree: {str(e)}")
      # Initialize empty trees to prevent further errors
      self.function_tree = {}
      self.top_level_commands = {}

  def _register_command_path(self, path, func):
    """Register a function at the given path in the function tree"""
    if not path:
      return

    current = self.function_tree
    path_so_far = []

    # Build the nested structure
    for part in path[:-1]:
      path_so_far.append(part)
      if part not in current:
        current[part] = {}
      current = current[part]

    # Add the leaf function
    leaf_name = path[-1]
    path_so_far.append(leaf_name)
    current[leaf_name] = {
      "function": func,
      "description": func._command_description,
      "help_text": func._command_help_text,
      "parameters": func._command_parameters,
      "returns": func._command_returns,
      "ai_callable": func._command_ai_callable
    }

  def execute(self, commands: list[str], settings: Settings) -> Result:
    """Execute a command by navigating the function tree and calling the appropriate function"""
    result = Result()

    # Navigate the function tree
    current = self.function_tree
    path = []

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
      for cmd in commands[1:]:
        if cmd.startswith("--"):
          # Handle flag
          flag_name = cmd[2:]
          kwargs[flag_name] = True
        elif "=" in cmd:
          # Handle key=value
          key, value = cmd.split("=", 1)
          kwargs[key] = value
        elif cmd in current:
          # Navigate tree
          current = current[cmd]
          path.append(cmd)
        else:
          # Positional argument
          args.append(cmd)
    else:
      self.help()
      return result

    # If we found a function, execute it
    if isinstance(current, dict) and "function" in current:
      func = current["function"]
      try:
        func_result = func(settings, *args, **kwargs)
        if isinstance(func_result, Result):
          result = func_result
      except Exception as e:
        result.fail(f"Error executing command: {str(e)}")
    else:
      self.unrecognizedCommand()

    return result

  def unrecognizedCommand(self) -> None:
    """Display message for unrecognized command"""
    print("Command incomplete or not recognized")

  def help(self) -> None:
    """Display help for this command, using help_text from decorators"""
    print(f"Here are the available {self.__class__.__name__.replace('Command', '').lower()} commands:")

    # Generate help dynamically from function tree
    # First, collect commands and their aliases
    command_groups = {}

    def collect_commands(tree, prefix=""):
      for name, node in tree.items():
        if "function" in node:
          # This is a leaf node (actual command)
          cmd_path = f"{prefix}{name}"
          help_text = node.get("help_text", "No help available")

          # Get the function object to check for aliases
          func = node.get("function")

          # Create a unique key for grouping based on the function object id
          func_id = id(func) if func else cmd_path

          if func_id not in command_groups:
            command_groups[func_id] = {
              "paths": [cmd_path],
              "help_text": help_text
            }
          else:
            command_groups[func_id]["paths"].append(cmd_path)
        else:
          # This is a branch node
          collect_commands(node, f"{prefix}{name} ")

    collect_commands(self.function_tree)

    # Display commands with their aliases grouped together
    for group in command_groups.values():
      paths = sorted(group["paths"])
      cmd_display = ", ".join(paths)
      help_text = group["help_text"]
      print(f"  {cmd_display}")
      print(f"    - {help_text}")

  def get_function_definitions(self) -> List[Dict[str, Any]]:
    """Get AI-callable function definitions for function calling"""
    definitions = []

    # Get the command class name (without the "Command" suffix)
    # For modules, use the module name instead
    if hasattr(self, '_module_name'):
      # This is a module command, use the module name
      class_prefix = self._module_name
    else:
      # This is a core command, use the class name
      class_prefix = self.__class__.__name__.replace("Command", "").lower()

    # Helper function to recursively process the function tree
    def process_tree(tree, path_parts):
      for name, node in tree.items():
        current_path = path_parts + [name]

        if isinstance(node, dict):
          if "function" in node and node.get("ai_callable", False):
            # This is a leaf node with a function
            # Create function name by joining class prefix and path parts with underscores
            # Format: prefix_path_part1_path_part2_...
            if len(path_parts) == 0:
              # Top-level command
              func_name = f"{class_prefix}_{name}"
            else:
              # Nested command
              func_name = f"{class_prefix}_{'_'.join(current_path)}"

            # Create function definition compatible with OpenAI format
            definition = {
              "name": func_name,
              "description": node["description"],
              "parameters": node["parameters"],
              "returns": node["returns"]
            }

            definitions.append(definition)
          else:
            # This is a branch node, continue traversing
            process_tree(node, current_path)

    try:
      # Start processing from the root with an empty path
      process_tree(self.function_tree, [])
    except Exception as e:
      print(f"Error processing function tree: {str(e)}")

    return definitions

  def get_top_level_commands(self) -> Dict[str, Callable]:
    """Get commands that should be registered at the top level"""
    return self.top_level_commands
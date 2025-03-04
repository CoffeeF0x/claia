from abc import ABC
from functools import wraps
from typing import List, Dict, Any, Callable, Optional

# Internal dependencies
from errors import Result
from settings import Settings



##################################################
#                COMMAND DECORATOR               #
##################################################
def command(
    path: List[str],
    description: str = None,
    help_text: str = None,
    parameters: Dict[str, Any] = None,
    returns: Dict[str, Any] = None,
    ai_callable: bool = True
):
  """
  Decorator for command methods. Registers a method as a command with metadata.

  Args:
    path: The command path (e.g., ["set"] or ["vllm", "zone"])
    description: Brief description of what the command does (used for AI function calling)
    help_text: Detailed help text shown to users (used for CLI help)
    parameters: JSON Schema for command parameters
    returns: JSON Schema for return value
    ai_callable: Whether this command can be called by AI via function calling
  """
  def decorator(func):
    func._command_path = path
    func._command_description = description or func.__doc__ or ""
    func._command_help_text = help_text or func._command_description
    func._command_parameters = parameters or {}
    func._command_returns = returns or {"type": "string"}
    func._command_ai_callable = ai_callable

    @wraps(func)
    def wrapper(*args, **kwargs):
      return func(*args, **kwargs)
    return wrapper
  return decorator



##################################################
#                   BASE CLASS                   #
##################################################
class Command(ABC):
  def __init__(self):
    """Initialize command and build the function tree from decorated methods"""
    self.function_tree = {}
    self._build_function_tree()

  def _build_function_tree(self):
    """Build command tree from methods decorated with @command"""
    for attr_name in dir(self):
      if attr_name.startswith('_'):
        continue

      attr = getattr(self, attr_name)
      if callable(attr) and hasattr(attr, '_command_path'):
        # Method has command metadata from decorator
        path = attr._command_path
        if not path:
          continue

        current = self.function_tree

        # Build the nested structure
        for part in path[:-1]:
          if part not in current:
            current[part] = {}
          current = current[part]

        # Add the leaf function
        leaf_name = path[-1]
        current[leaf_name] = {
          "function": attr,
          "description": attr._command_description,
          "help_text": attr._command_help_text,
          "parameters": attr._command_parameters,
          "returns": attr._command_returns,
          "ai_callable": attr._command_ai_callable
        }

  def execute(self, commands: list[str], settings: Settings) -> Result:
    """Execute a command by navigating the function tree and calling the appropriate function"""
    result = Result()
    if len(commands) <= 1:
      self.help()
      return result

    # Navigate the function tree
    current = self.function_tree
    path = []

    # Parse arguments and flags
    args = []
    kwargs = {}

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
    def print_commands(tree, prefix=""):
      for name, node in sorted(tree.items()):
        if "function" in node:
          # This is a leaf node (actual command)
          cmd_path = f"{prefix}{name}"
          help_text = node.get("help_text", "No help available")
          print(f"  {cmd_path}")
          print(f"    - {help_text}")
        else:
          # This is a branch node
          print_commands(node, f"{prefix}{name} ")

    print_commands(self.function_tree)

  def get_function_definitions(self) -> List[Dict[str, Any]]:
    """Get AI-callable function definitions for function calling"""
    definitions = []

    def process_tree(tree, path_prefix):
      for name, node in tree.items():
        if "function" in node and node.get("ai_callable", False):
          # Create path string for the function name
          func_name = f"{path_prefix}_{name}" if path_prefix else name

          # Create function definition compatible with OpenAI format
          definition = {
            "name": func_name,
            "description": node["description"],
            "parameters": node["parameters"],
            "returns": node["returns"]
          }
          definitions.append(definition)
        elif isinstance(node, dict):
          # Process nested paths
          new_prefix = f"{path_prefix}_{name}" if path_prefix else name
          process_tree(node, new_prefix)

    process_tree(self.function_tree, "")
    return definitions

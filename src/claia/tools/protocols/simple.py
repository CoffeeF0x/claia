"""
Simple protocol: resolve tool name to a command module plugin (supports grouped
commands via dotted names) and execute it, returning a common Result.
"""

import logging
from typing import Dict, Any
import pluggy

from claia.tools.hooks.protocol import ProtocolHooks, ProtocolInfo
from claia.common.results import Result

hookimpl = pluggy.HookimplMarker("claia_tool_protocols")
logger = logging.getLogger(__name__)


class SimpleProtocolPlugin:
  @hookimpl
  def get_protocol_info(self) -> ProtocolInfo:
    return ProtocolInfo(
      name="simple",
      title="Simple Local Protocol",
      description="Resolves tool name to a command module plugin and executes it.",
      required_args=[],
    )

  @hookimpl
  def execute(self, tool_name: str, parameters: Dict[str, Any], conversation, manager, **kwargs) -> Result:
    # Use the new hierarchical command resolution system
    module_plugin, command_def, module_info = manager.get_command_by_name(tool_name)

    if not module_plugin or not command_def:
      return Result.fail(f"Command '{tool_name}' not found")

    # Filter kwargs based on module's required_args
    filtered_kwargs = {}
    if getattr(module_info, 'required_args', None):
      for k in module_info.required_args:
        if k in kwargs:
          filtered_kwargs[k] = kwargs[k]

    # Validate arguments using ArgumentDefinition structure
    missing_args = []
    type_errors = []
    validated_params = {}

    for arg_name, arg_def in command_def.arguments.items():
      param_value = (parameters or {}).get(arg_name)

      # Check if required argument is missing
      if arg_def.required and param_value is None:
        missing_args.append(f"{arg_name} ({arg_def.description})")
        continue

      # Use default value if provided and parameter is missing
      if param_value is None and arg_def.default_value is not None:
        param_value = arg_def.default_value

      # Skip type validation if parameter is None
      if param_value is None:
        validated_params[arg_name] = param_value
        continue

      # Validate data type
      try:
        if arg_def.data_type == "str":
          validated_params[arg_name] = str(param_value)
        elif arg_def.data_type == "int":
          validated_params[arg_name] = int(float(param_value))  # Handle "3.0" -> 3
        elif arg_def.data_type == "float":
          validated_params[arg_name] = float(param_value)
        elif arg_def.data_type == "bool":
          if isinstance(param_value, bool):
            validated_params[arg_name] = param_value
          elif str(param_value).lower() in ("true", "1", "yes", "on"):
            validated_params[arg_name] = True
          elif str(param_value).lower() in ("false", "0", "no", "off"):
            validated_params[arg_name] = False
          else:
            raise ValueError(f"Cannot convert '{param_value}' to boolean")
        else:  # "custom" or other types
          validated_params[arg_name] = param_value
      except (ValueError, TypeError) as e:
        type_errors.append(f"{arg_name}: expected {arg_def.data_type}, got {type(param_value).__name__} ({e})")

    # Report validation errors
    if missing_args:
      return Result.fail(f"Missing required arguments for '{tool_name}': {', '.join(missing_args)}")
    if type_errors:
      return Result.fail(f"Type validation errors for '{tool_name}': {'; '.join(type_errors)}")

    # Use validated parameters
    parameters = validated_params

    # Execute the command using its registered callable
    try:
      # Pass validated parameters as keyword arguments along with filtered_kwargs
      all_kwargs = {**(parameters or {}), **filtered_kwargs}
      data = command_def.callable(**all_kwargs)
      return Result.ok(data)
    except Exception as e:
      logger.exception(f"Error executing command '{tool_name}'")
      return Result.fail(str(e))

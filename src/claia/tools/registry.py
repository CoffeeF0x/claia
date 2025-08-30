"""
ToolsRegistry is the single point of interaction for the tools package.

Responsibilities:
- Load and coordinate tool pattern/protocol plugins
- Detect and execute tool calls inside content
- Discover, cache, and execute command modules (for CLI and tool-calling)
"""

import logging
import json
from typing import Any, Dict, Optional

from .manager import ToolsManager
from claia.common.enums.conversation import ActionType
from claia.common.results import Result


logger = logging.getLogger(__name__)


class ToolsRegistry:
  def __init__(self, manager: Optional[ToolsManager] = None):
    self.manager = manager or ToolsManager()
    self._commands_catalog: Optional[Dict[str, Dict]] = None

  def _ensure_loaded(self) -> None:
    """Ensure plugins are loaded and commands catalog is built."""
    self.manager.load_all()
    if self._commands_catalog is None:
      self._commands_catalog = self.manager.get_all_commands()

  def get_commands_catalog(self) -> Dict[str, Dict]:
    """Return a cached catalog of all commands grouped by module."""
    self._ensure_loaded()
    return self._commands_catalog or {}

  def contains_tool_tokens(self, content: str, pattern_name: Optional[str] = None) -> bool:
    """Lightweight precheck to see if content likely contains tool calls for a pattern."""
    self._ensure_loaded()
    pattern_plugin = None
    pattern_info = None
    if pattern_name:
      pattern_plugin, pattern_info = self.manager.get_pattern_by_name(pattern_name)
    if not pattern_plugin:
      pattern_plugin = self.manager.get_default_pattern()
      if pattern_plugin:
        pattern_info = pattern_plugin.get_pattern_info()
    if not pattern_plugin or not pattern_info:
      return False
    opening_token = getattr(pattern_info, 'opening_token', None)
    if not opening_token:
      return False
    return opening_token in content

  def process_content(self, conversation, content: str, settings=None, protocol_name: str = 'simple', **kwargs) -> str:
    """
    Find and execute tool calls in content using the configured pattern/protocol.
    """
    self._ensure_loaded()

    # Resolve pattern plugin: prefer conversation pattern name, fallback to default
    pattern_plugin = None
    pattern_info = None
    try:
      if conversation and getattr(conversation, 'tool_pattern_name', None):
        pattern_plugin, pattern_info = self.manager.get_pattern_by_name(conversation.tool_pattern_name)
    except Exception:
      pattern_plugin, pattern_info = None, None
    if not pattern_plugin:
      pattern_plugin = self.manager.get_default_pattern()
      if pattern_plugin:
        pattern_info = pattern_plugin.get_pattern_info()
    if not pattern_plugin:
      logger.debug("No tool pattern plugins registered; returning content unchanged")
      return content

    # Resolve protocol plugin
    protocol_plugin, protocol_info = self.manager.get_protocol_by_name(protocol_name)
    if not protocol_plugin:
      logger.warning(f"Tool protocol '{protocol_name}' not found; returning content unchanged")
      return content

    # Filter kwargs for protocol if it requests required_args
    filtered_protocol_kwargs = self._filter_kwargs(kwargs, getattr(protocol_info, 'required_args', None))

    processed = content

    # Iterate until no more matches are found
    while True:
      matches = pattern_plugin.find_tool_calls(processed, conversation, settings=settings)
      if not matches:
        break

      # Process matches in order, left-to-right to keep indices consistent
      for m in matches:
        try:
          exec_result: Result = protocol_plugin.execute(
            m.tool_name,
            m.parameters or {},
            conversation,
            self.manager,
            **filtered_protocol_kwargs
          )
        except Exception as e:
          exec_result = Result.fail(str(e))

        if exec_result.is_success():
          data = exec_result.get_data()
          if isinstance(data, str):
            replacement = data
          elif data is None:
            replacement = ''
          else:
            try:
              replacement = json.dumps(data)
            except Exception:
              replacement = str(data)
        else:
          replacement = f"[TOOL_ERROR] {exec_result.get_message() or 'Unknown tool error'}"

        # Log action on conversation
        try:
          conversation.add_action(ActionType.PROCESS_FUNCTION_CALL, {
            "tool_name": m.tool_name,
            "parameters": m.parameters,
            "result_preview": (replacement[:100] + "...") if len(replacement) > 100 else replacement
          })
        except Exception:
          logger.debug("Failed to add action for tool execution; continuing")

        # Replace text span
        processed = processed[:m.start_index] + replacement + processed[m.end_index:]

      # Continue loop to detect nested or newly introduced calls

    return processed

  def run_command(self, command_name: str, parameters: Dict[str, Any], conversation, **kwargs) -> Result:
    """Execute a command module by name (for CLI use) with arg filtering."""
    self._ensure_loaded()

    plugin, cmd_def, module_info = self.manager.get_command_by_name(command_name)
    if not plugin or not (cmd_def or hasattr(plugin, 'run')):
      return Result.fail(f"Command not found: {command_name}")

    # Filter kwargs against module's required args (if any)
    filtered_kwargs = self._filter_kwargs(kwargs, getattr(module_info, 'required_args', None))

    try:
      if cmd_def and hasattr(cmd_def, 'callable') and callable(cmd_def.callable):
        # Prepare keyword args for the callable based on its command definition
        call_kwargs = self._prepare_command_kwargs(parameters or {}, cmd_def)

        # Inject conversation only if the module explicitly requires it
        req = getattr(module_info, 'required_args', None) if module_info else None
        if req and 'conversation' in req:
          call_kwargs['conversation'] = conversation

        # Merge any filtered module-level kwargs (e.g., API keys)
        call_kwargs.update(filtered_kwargs)

        data = cmd_def.callable(**call_kwargs)
      else:
        # Legacy single-command module keeps legacy signature
        data = plugin.run(parameters or {}, conversation, **filtered_kwargs)
      return Result.ok(data=data)
    except Exception as e:
      return Result.fail(str(e))

  def _filter_kwargs(self, kwargs: Dict[str, Any], required_args: Optional[list]) -> Dict[str, Any]:
    if not required_args:
      return {}
    return {k: v for k, v in kwargs.items() if k in required_args}

  def _prepare_command_kwargs(self, parameters: Dict[str, Any], cmd_def) -> Dict[str, Any]:
    """Map CLI-provided parameters to the callable's expected arguments.

    Supports both key=value style and positional tokens provided under
    the special key '__args__' (a list of raw string tokens).
    """
    args_spec = getattr(cmd_def, 'arguments', None) or {}
    # Preserve insertion order of args_spec (Python 3.7+ dicts are ordered)
    pos_vals = []
    if isinstance(parameters, dict) and '__args__' in parameters and isinstance(parameters['__args__'], list):
      pos_vals = list(parameters['__args__'])

    call_kwargs: Dict[str, Any] = {}

    for name, arg_def in args_spec.items():
      provided = None
      # 1) explicit key=value takes precedence
      if name in parameters:
        provided = parameters[name]
      # 2) use positional if available
      elif pos_vals:
        provided = pos_vals.pop(0)
      # 3) default value if present and not provided
      elif hasattr(arg_def, 'default_value') and getattr(arg_def, 'default_value') is not None:
        provided = getattr(arg_def, 'default_value')

      # Validate required
      required = getattr(arg_def, 'required', False)
      if provided is None and required:
        raise ValueError(f"Missing required argument: {name}")

      if provided is not None:
        dtype = getattr(arg_def, 'data_type', 'str')
        call_kwargs[name] = self._convert_type(provided, dtype)

    return call_kwargs

  def _convert_type(self, value: Any, data_type: str) -> Any:
    """Convert string value to the requested data type.

    Supports: 'str', 'int', 'float', 'bool'. Falls back to str.
    """
    try:
      if data_type == 'int':
        return int(value)
      if data_type == 'float':
        return float(value)
      if data_type == 'bool':
        if isinstance(value, bool):
          return value
        v = str(value).strip().lower()
        if v in ('1', 'true', 't', 'yes', 'y', 'on'):
          return True
        if v in ('0', 'false', 'f', 'no', 'n', 'off'):
          return False
        # Non-standard bool: treat non-empty as True
        return bool(v)
      # default and 'str'
      return str(value)
    except Exception:
      # If conversion fails, return original value
      return value

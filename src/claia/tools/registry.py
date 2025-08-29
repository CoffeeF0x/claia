"""
ToolsRegistry coordinates pattern detection and protocol execution for tools.
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

  def process_content(self, conversation, content: str, settings=None, protocol_name: str = 'simple', **kwargs) -> str:
    """
    Find and execute tool calls in content using the configured pattern/protocol.
    """
    self.manager.load_all()

    pattern = self.manager.get_default_pattern()
    if not pattern:
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
    offset = 0

    # We will iterate until no more matches are found
    while True:
      matches = pattern.find_tool_calls(processed, conversation, settings=settings)
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

  def _filter_kwargs(self, kwargs: Dict[str, Any], required_args: Optional[list]) -> Dict[str, Any]:
    if not required_args:
      return {}
    return {k: v for k, v in kwargs.items() if k in required_args}

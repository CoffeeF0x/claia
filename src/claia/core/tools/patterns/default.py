"""
Default tool-calling pattern that finds [TOOL_CALL]{...}[/TOOL_CALL] JSON
blocks and parses them into ToolCallMatch objects.
"""

import json
import logging
from typing import List
import pluggy

from ...plugins.base import PatternInfo, ToolCallMatch
from claia.core.data.utils.tool_text import find_tool_calls as find_tag_spans

hookimpl = pluggy.HookimplMarker("claia_tool_patterns")
logger = logging.getLogger(__name__)


class DefaultToolPatternPlugin:
  @hookimpl
  def get_pattern_info(self) -> PatternInfo:
    prompt = (
      "You can call tools by emitting exactly one TOOL_CALL block when needed.\n"
      "Use this exact format and valid JSON inside the block:\n\n"
      "{tool_format}\n\n"
      "Available tools you may call (name, description, parameters, returns):\n"
      "{tool_definitions}\n\n"
      "Rules:\n"
      "- Only emit a {opening}...{closing} block when you need to run a tool.\n"
      "- Do not wrap or explain around the block; emit the block alone.\n"
      "- If you don't need a tool, write a normal answer with no TOOL_CALL.\n"
      "- Parameters must be valid JSON.\n"
    )

    return PatternInfo(
      name="default",
      title="Default Tag Pattern",
      description="Parses [TOOL_CALL]{...}[/TOOL_CALL] JSON blocks",
      opening_token="[TOOL_CALL]",
      closing_token="[/TOOL_CALL]",
      prompt_template=prompt.replace("{opening}", "[TOOL_CALL]").replace("{closing}", "[/TOOL_CALL]")
    )

  @hookimpl
  def find_tool_calls(self, content: str, conversation, settings=None) -> List[ToolCallMatch]:
    matches: List[ToolCallMatch] = []

    spans = find_tag_spans(content, "[TOOL_CALL]", "[/TOOL_CALL]")

    for span in spans:
      if not span['content']:
        continue
      try:
        data = json.loads(span['content'])
        name = data.get('name') or data.get('tool') or ''
        params = data.get('parameters') or {}
        if name:
          matches.append(ToolCallMatch(
            start_index=span['start_index'],
            end_index=span['end_index'],
            tool_name=name,
            parameters=params,
            raw=span['content']
          ))
      except json.JSONDecodeError:
        logger.warning("Malformed JSON inside TOOL_CALL block; skipping")
      except Exception as e:
        logger.warning(f"Error parsing TOOL_CALL: {e}")

    matches.sort(key=lambda m: m.start_index)
    return matches

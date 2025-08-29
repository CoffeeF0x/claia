"""
Default tool-calling pattern that reuses Conversation.find_tags() and
parses JSON inside TOOL_CALL tags.
"""

import json
import logging
from typing import List
import pluggy

from claia.tools.hooks.pattern import PatternHooks, PatternInfo, ToolCallMatch
from claia.common.enums.conversation import TagType, TagStatus

hookimpl = pluggy.HookimplMarker("claia_tool_patterns")
logger = logging.getLogger(__name__)


class DefaultToolPatternPlugin:
  @hookimpl
  def get_pattern_info(self) -> PatternInfo:
    return PatternInfo(
      name="default",
      title="Default Tag Pattern",
      description="Parses [TOOL_CALL]{...}[/TOOL_CALL] JSON blocks using Conversation.find_tags()",
      opening_token="[TOOL_CALL]",
      closing_token="[/TOOL_CALL]"
    )

  @hookimpl
  def find_tool_calls(self, content: str, conversation, settings=None) -> List[ToolCallMatch]:
    matches: List[ToolCallMatch] = []
    try:
      tags = conversation.find_tags(content)
    except Exception as e:
      logger.warning(f"find_tags failed: {e}")
      return matches

    for t in tags:
      if t['type'] == TagType.TOOL_CALL and t['status'] == TagStatus.CLOSED and t['content']:
        try:
          data = json.loads(t['content'])
          name = data.get('name') or data.get('tool') or ''
          params = data.get('parameters') or {}
          if name:
            matches.append(ToolCallMatch(
              start_index=t['start_index'],
              end_index=t['end_index'],
              tool_name=name,
              parameters=params,
              raw=t['content']
            ))
        except json.JSONDecodeError:
          logger.warning("Malformed JSON inside TOOL_CALL block; skipping")
        except Exception as e:
          logger.warning(f"Error parsing TOOL_CALL: {e}")

    # Sort by start index for deterministic processing
    matches.sort(key=lambda m: m.start_index)
    return matches

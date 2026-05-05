"""
Default tag specifications.

Exactly one ``TagSpec`` per ``TagType`` is registered as the global
default. Per-model overrides supersede these (see
``claia.core.parser.resolution``). There is never more than one
spec of a given ``TagType`` active in a parser instance.
"""

from typing import Dict

from .types import TagSpec, TagType


########################################################################
#                            DEFAULT TAGS                              #
########################################################################
DEFAULT_TAGS: Dict[TagType, TagSpec] = {
  TagType.TOOL: TagSpec(
    tag_type=TagType.TOOL,
    open_token="[TOOL_CALL]",
    close_token="[/TOOL_CALL]",
  ),
  TagType.THINKING: TagSpec(
    tag_type=TagType.THINKING,
    open_token="<think>",
    close_token="</think>",
  ),
  TagType.REFERENCE: TagSpec(
    tag_type=TagType.REFERENCE,
    open_token="[REF]",
    close_token="[/REF]",
  ),
}

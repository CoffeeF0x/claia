"""
Generate-time system prompt composition for agents.

Agents own the policy: a persona string plus, when tools are loaded,
MANUAL-mode calling instructions that match the active ``TagSpec``.
``Registry.run(..., system=...)`` forwards the composed string; this
module is how agents build it.
"""

from typing import Any, Dict, Iterable, List, Optional

from ...core.enums.parser import TagType
from ...core.parser.types import TagSpec
from ...core.plugins.base import ArgumentDefinition, ToolReference


########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."

# Host injectables that tools may declare but the model must not send.
_INJECTABLE_ARGS = frozenset({
  "registry",
  "conversation",
  "settings",
  "command_specs",
  "current_mode",
  "kwargs",
})


########################################################################
#                              COMPOSERS                               #
########################################################################
def compose_system_prompt(
  system: Optional[str] = None,
  *,
  tools: Optional[Iterable[ToolReference]] = None,
  tag_specs: Optional[Iterable[TagSpec]] = None,
) -> str:
  """Build the generate-time ``system`` string for an agent turn.

  Tool-calling instructions are prepended when both a TOOL ``TagSpec``
  and a non-empty tool list are present. The persona is ``system`` if
  it has content, otherwise ``DEFAULT_SYSTEM_PROMPT``.
  """
  persona = (system or "").strip() or DEFAULT_SYSTEM_PROMPT
  instructions = render_tool_instructions(
    list(tools or []),
    list(tag_specs or []),
  )
  if not instructions:
    return persona
  return f"{instructions}\n\n{persona}"


def render_tool_instructions(
  tools: List[ToolReference],
  tag_specs: List[TagSpec],
) -> str:
  """Return MANUAL-mode calling instructions, or ``""`` if none apply."""
  if not tools:
    return ""
  spec = _tool_spec(tag_specs)
  if spec is None:
    return ""

  lines = [
    "You can call tools by writing a tool-call tag in your reply.",
    "Use this exact format:",
    "",
    spec.open_token,
    '{"name": "<qualified tool name>", "parameters": { ... }}',
    spec.close_token,
    "",
    "Call one tool at a time. The next user message is the tool result",
    "in a [TOOL_RESULT] tag — not a new human request. Continue: call",
    "another tool the same way, or answer the user. Do not invent tools.",
    "",
    "Available tools:",
  ]
  for tool in tools:
    lines.extend(_format_tool(tool))
  return "\n".join(lines)


def format_tool_result(name: str, body: str) -> str:
  """Render a tool result as a user-turn ``[TOOL_RESULT]`` block."""
  label = (name or "").strip() or "unknown"
  return f'[TOOL_RESULT name="{label}"]\n{body}\n[/TOOL_RESULT]'


########################################################################
#                              INTERNALS                               #
########################################################################
def _tool_spec(tag_specs: Iterable[TagSpec]) -> Optional[TagSpec]:
  for spec in tag_specs:
    if spec.tag_type is TagType.TOOL:
      return spec
  return None


def _format_tool(tool: ToolReference) -> List[str]:
  name = tool.qualified_name
  description = (tool.description or "").strip()
  header = f"- {name}: {description}" if description else f"- {name}"
  lines = [header]
  lines.extend(_format_arguments(tool.parameter_schema))
  return lines


def _format_arguments(schema: Any) -> List[str]:
  if not schema:
    return []

  if isinstance(schema, dict):
    if _looks_like_json_schema(schema):
      return _format_json_schema_args(schema)
    lines = []
    for name, spec in schema.items():
      if name in _INJECTABLE_ARGS:
        continue
      formatted = _format_one_argument(name, spec)
      if formatted:
        lines.append(formatted)
    return lines

  return []


def _looks_like_json_schema(schema: Dict[str, Any]) -> bool:
  return "properties" in schema and isinstance(schema.get("properties"), dict)


def _format_json_schema_args(schema: Dict[str, Any]) -> List[str]:
  required = set(schema.get("required") or [])
  lines = []
  for name, spec in (schema.get("properties") or {}).items():
    if name in _INJECTABLE_ARGS or not isinstance(spec, dict):
      continue
    type_name = spec.get("type") or "any"
    req = "required" if name in required else "optional"
    desc = (spec.get("description") or "").strip()
    line = f"  - {name} ({type_name}, {req})"
    if desc:
      line += f": {desc}"
    lines.append(line)
  return lines


def _format_one_argument(name: str, spec: Any) -> Optional[str]:
  if isinstance(spec, ArgumentDefinition):
    req = "required" if spec.required else "optional"
    line = f"  - {name} ({spec.data_type}, {req})"
    if not spec.required and spec.default_value is not None:
      line += f", default={spec.default_value!r}"
    desc = (spec.description or "").strip()
    if desc:
      line += f": {desc}"
    return line

  if isinstance(spec, dict):
    type_name = spec.get("data_type") or spec.get("type") or "any"
    required = bool(spec.get("required", False))
    req = "required" if required else "optional"
    line = f"  - {name} ({type_name}, {req})"
    desc = (spec.get("description") or "").strip()
    if desc:
      line += f": {desc}"
    return line

  return None

"""
Provider-native tool calling helpers for hosted API architectures.

Converts ``ToolReference`` catalogs into each provider's ``tools``
array, maps TOOL utilities onto that provider's follow-up wire, and
parses native call payloads into ``ToolChunk``.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from ...data.chunks import ToolChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...enums.conversation import MessageRole
from ...enums.plugins import ParamCategory, ParamScope
from ...plugins.base import ArgumentDefinition, ParamSpec, ToolReference


########################################################################
#                              CONSTANTS                               #
########################################################################
# Same names the agent strips from MANUAL instructions. Core cannot
# import the agent; keep the set here so providers never see injectables.
_INJECTABLE = frozenset({
  "registry",
  "conversation",
  "settings",
  "command_specs",
  "current_mode",
  "kwargs",
})

_JSON_TYPES = {
  "str": "string",
  "string": "string",
  "int": "integer",
  "integer": "integer",
  "float": "number",
  "number": "number",
  "bool": "boolean",
  "boolean": "boolean",
}

TOOLS_PARAM = ParamSpec(
  name="tools",
  type=list,
  scope=ParamScope.RUNTIME,
  default=None,
  externally_settable=False,
  category=ParamCategory.GENERATION,
  description="ToolReference list for provider-native tool calling.",
)


########################################################################
#                           SCHEMA / ARRAYS                            #
########################################################################
def json_schema_from_tool(ref: ToolReference) -> Dict[str, Any]:
  """JSON Schema object for one tool's parameters."""
  schema = ref.parameter_schema
  if not schema:
    return {"type": "object", "properties": {}}
  if isinstance(schema, dict) and _looks_like_json_schema(schema):
    return _strip_injectable_schema(schema)
  if isinstance(schema, dict):
    return _schema_from_argument_map(schema)
  return {"type": "object", "properties": {}}


def openai_responses_tools(refs: Iterable[ToolReference]) -> List[Dict[str, Any]]:
  """Responses API ``tools`` array."""
  return [
    {
      "type": "function",
      "name": ref.qualified_name,
      "description": ref.description or "",
      "parameters": json_schema_from_tool(ref),
    }
    for ref in refs
  ]


def openai_chat_tools(refs: Iterable[ToolReference]) -> List[Dict[str, Any]]:
  """Chat Completions / OpenRouter ``tools`` array."""
  return [
    {
      "type": "function",
      "function": {
        "name": ref.qualified_name,
        "description": ref.description or "",
        "parameters": json_schema_from_tool(ref),
      },
    }
    for ref in refs
  ]


def anthropic_tools(refs: Iterable[ToolReference]) -> List[Dict[str, Any]]:
  """Anthropic Messages ``tools`` array."""
  return [
    {
      "name": ref.qualified_name,
      "description": ref.description or "",
      "input_schema": json_schema_from_tool(ref),
    }
    for ref in refs
  ]


########################################################################
#                         NATIVE FOLLOW-UP WIRE                        #
########################################################################
def format_openai_responses_input(sequence: MessageSequence) -> List[Dict[str, Any]]:
  """Responses API ``input`` items, including function-call pairs."""
  items: List[Dict[str, Any]] = []
  for message in sequence.messages:
    if message.role == MessageRole.SYSTEM:
      continue
    if message.role == MessageRole.UTILITY:
      call = native_call_from_utility(message)
      if call is None:
        continue
      items.append({
        "type": "function_call",
        "call_id": call["call_id"],
        "name": call["name"],
        "arguments": json.dumps(call["arguments"]),
      })
      items.append({
        "type": "function_call_output",
        "call_id": call["call_id"],
        "output": call["result"],
      })
      continue
    if message.role in (MessageRole.USER, MessageRole.ASSISTANT) and message.content:
      items.append({"role": message.role.value, "content": message.content})
  return items


def format_openai_chat_messages(sequence: MessageSequence) -> List[Dict[str, Any]]:
  """Chat Completions messages with ``tool_calls`` / ``role=tool``."""
  formatted: List[Dict[str, Any]] = []
  for message in sequence.messages:
    if message.role == MessageRole.SYSTEM:
      continue
    if message.role == MessageRole.UTILITY:
      call = native_call_from_utility(message)
      if call is None:
        continue
      tool_call = {
        "id": call["call_id"],
        "type": "function",
        "function": {
          "name": call["name"],
          "arguments": json.dumps(call["arguments"]),
        },
      }
      assistant = _last_role(formatted, "assistant")
      if assistant is None:
        assistant = {"role": "assistant", "content": None, "tool_calls": []}
        formatted.append(assistant)
      assistant.setdefault("tool_calls", []).append(tool_call)
      if not assistant.get("content"):
        assistant["content"] = None
      formatted.append({
        "role": "tool",
        "tool_call_id": call["call_id"],
        "content": call["result"],
      })
      continue
    if message.role in (MessageRole.USER, MessageRole.ASSISTANT) and message.content:
      formatted.append({"role": message.role.value, "content": message.content})
  return formatted


def format_anthropic_messages(sequence: MessageSequence) -> List[Dict[str, Any]]:
  """Anthropic messages with ``tool_use`` / ``tool_result`` blocks."""
  formatted: List[Dict[str, Any]] = []
  for message in sequence.messages:
    if message.role == MessageRole.SYSTEM:
      continue
    if message.role == MessageRole.UTILITY:
      call = native_call_from_utility(message)
      if call is None:
        continue
      tool_use = {
        "type": "tool_use",
        "id": call["call_id"],
        "name": call["name"],
        "input": call["arguments"],
      }
      assistant = _last_role(formatted, "assistant")
      if assistant is None:
        assistant = {"role": "assistant", "content": []}
        formatted.append(assistant)
      _append_anthropic_block(assistant, tool_use)

      result_block = {
        "type": "tool_result",
        "tool_use_id": call["call_id"],
        "content": call["result"],
      }
      last = formatted[-1] if formatted else None
      if last is not None and last.get("role") == "user" and isinstance(last.get("content"), list):
        last["content"].append(result_block)
      else:
        formatted.append({"role": "user", "content": [result_block]})
      continue
    if message.role in (MessageRole.USER, MessageRole.ASSISTANT) and message.content:
      formatted.append({"role": message.role.value, "content": message.content})
  return formatted


########################################################################
#                              PARSING                                 #
########################################################################
def parse_arguments(raw: Any) -> Dict[str, Any]:
  """Coerce a provider arguments payload to a dict."""
  if isinstance(raw, dict):
    return raw
  if not raw:
    return {}
  if isinstance(raw, str):
    try:
      parsed = json.loads(raw)
    except json.JSONDecodeError:
      return {}
    return parsed if isinstance(parsed, dict) else {}
  return {}


def tool_chunk(
  name: Optional[str],
  arguments: Any,
  call_id: Optional[str] = None,
) -> ToolChunk:
  """Build a ``ToolChunk`` from a native provider call."""
  return ToolChunk(
    tool_name=(name or "").strip(),
    payload=parse_arguments(arguments),
    call_id=call_id,
  )


def native_call_from_utility(message) -> Optional[Dict[str, Any]]:
  """Extract name / call_id / arguments / result from a TOOL utility."""
  artifacts = getattr(message, "tool_result_artifacts", lambda: [])()
  if not artifacts:
    return None
  artifact = artifacts[0]
  name = (artifact.tool_name or "").strip()
  call_id = artifact.call_id or getattr(artifact, "guid", None) or getattr(
    message, "message_id", None
  )
  args: Any = {}
  try:
    envelope = json.loads(message.content or "")
  except (TypeError, json.JSONDecodeError):
    envelope = None
  if isinstance(envelope, dict):
    args = envelope.get("parameters", envelope)
    if not name:
      name = (envelope.get("name") or "").strip()
  if not isinstance(args, dict):
    args = {}
  return {
    "name": name,
    "call_id": call_id or name or "tool",
    "arguments": args,
    "result": artifact.payload_text(),
  }


########################################################################
#                              INTERNAL                                #
########################################################################
def _looks_like_json_schema(schema: Dict[str, Any]) -> bool:
  return "properties" in schema and isinstance(schema.get("properties"), dict)


def _strip_injectable_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
  properties = {
    name: spec
    for name, spec in (schema.get("properties") or {}).items()
    if name not in _INJECTABLE
  }
  required = [
    name for name in (schema.get("required") or [])
    if name in properties
  ]
  out = {**schema, "type": schema.get("type") or "object", "properties": properties}
  if required:
    out["required"] = required
  else:
    out.pop("required", None)
  return out


def _schema_from_argument_map(schema: Dict[str, Any]) -> Dict[str, Any]:
  properties: Dict[str, Any] = {}
  required: List[str] = []
  for name, spec in schema.items():
    if name in _INJECTABLE:
      continue
    if isinstance(spec, ArgumentDefinition):
      properties[name] = {
        "type": _JSON_TYPES.get(spec.data_type, "string"),
        "description": spec.description or "",
      }
      if spec.required:
        required.append(name)
      continue
    if isinstance(spec, dict):
      properties[name] = spec
      if spec.get("required"):
        required.append(name)
  out: Dict[str, Any] = {"type": "object", "properties": properties}
  if required:
    out["required"] = required
  return out


def _last_role(formatted: List[Dict[str, Any]], role: str) -> Optional[Dict[str, Any]]:
  for item in reversed(formatted):
    if item.get("role") == role:
      return item
  return None


def _append_anthropic_block(assistant: Dict[str, Any], block: Dict[str, Any]) -> None:
  content = assistant.get("content")
  if isinstance(content, list):
    content.append(block)
    return
  if isinstance(content, str) and content:
    assistant["content"] = [{"type": "text", "text": content}, block]
    return
  assistant["content"] = [block]

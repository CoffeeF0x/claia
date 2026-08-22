"""
Agent loop tests.

End-to-end coverage of the agent loop that owns the per-turn
``TagParser`` and dispatches tool calls inline through
``Registry.execute_tool``:

- Streaming text-only response (no tags).
- Streaming with one tool call.
- Streaming with multiple tool calls.
- Streaming with thinking + tool call mixed.

Also exercises the surrounding plumbing:

- ``Registry.resolve_qualified_name`` for bare → qualified name
  resolution.
- Parser-event handling for ``ParseError`` / ``TextEvent``.
- Tag content split across chunk boundaries still yields a single
  ``TagEvent``.
- Bound utility messages mirror each closed tag.
- Tool dispatch failures surface as inline ``[TOOL_ERROR]`` text and
  still fire a utility message for the call itself.
- The final ``parser.flush()`` pass dispatches a tool call that
  closed on the very last chunk.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from claia.core.data import Conversation
from claia.core.enums.conversation import MessageRole
from claia.core.enums.parser import TagType
from claia.core.enums.task import TaskEvent, TaskStatus
from claia.core.data.chunks import BaseChunk, TextChunk
from claia.core.plugins.base import ToolReference
from claia.core.results import Result
from claia.framework.agents.simple import SimpleAgent
from claia.framework.task import Task


def _utilities(convo) -> List[Any]:
  """Return only the ``UTILITY``-role messages from a conversation.

  ``Message.is_utility`` is a *method* (not a property), so a naive
  ``if m.is_utility`` truthy-check passes for every message. Wrap the
  filter once here so each test reads cleanly.
  """
  return [m for m in convo.messages if m.role == MessageRole.UTILITY]


def _assistant_message(convo):
  """Return the most recent assistant message.

  ``Conversation.get_latest_message`` returns the active head, which
  becomes a ``UTILITY`` message after each ``append_utility`` call.
  Tests that want the streaming assistant message specifically need
  to filter explicitly.
  """
  for msg in reversed(convo.messages):
    if msg.role == MessageRole.ASSISTANT:
      return msg
  return None


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------
class _FakeToolRegistry:
  """Minimal registry surface the agent reaches for during a turn.

  Only the methods the agent loop actually calls are implemented:
  ``run`` (the deployment stream), ``get_supported_models`` (for
  tag-spec resolution — returning ``{}`` falls back to defaults),
  ``execute_tool`` (the dispatch sink), and
  ``resolve_qualified_name`` (bare-name fallback).
  """

  def __init__(self, chunks: List[BaseChunk], tools: Optional[Dict[str, Any]] = None):
    self._chunks = chunks
    # ``tools`` maps qualified_name -> callable(payload, conversation, **kw) -> Result
    self._tools: Dict[str, Any] = tools or {}
    self.execute_calls: List[Dict[str, Any]] = []

  def run(self, model_id, conversation, streaming=False, **kwargs):
    assert streaming is True
    return iter(self._chunks)

  def get_supported_models(self):
    # Empty mapping -> resolve_tag_specs falls back to DEFAULT_TAGS
    return {}

  def resolve_qualified_name(self, name: str) -> Optional[str]:
    if name in self._tools:
      return name
    # Bare-name fallback: first qualified entry ending with ".<name>".
    suffix = "." + name
    for q in self._tools:
      if q.endswith(suffix):
        return q
    return None

  def execute_tool(self, qualified_name, raw_payload, conversation, **kwargs):
    self.execute_calls.append({
      "qualified_name": qualified_name,
      "raw_payload": raw_payload,
      "kwargs": kwargs,
    })
    fn = self._tools.get(qualified_name)
    if fn is None:
      return Result.fail(f"Tool not found: {qualified_name}")
    return fn(raw_payload, conversation, **kwargs)


def _task(conversation, model_id="dummy-model"):
  return Task(conversation=conversation, parameters={"model_id": model_id})


def _stream(*texts: str, conversation_factory=Conversation):
  """Build a one-shot list of ``TextChunk`` items from text snippets."""
  del conversation_factory
  return [TextChunk(data=t) for t in texts]


# ---------------------------------------------------------------------------
# Scenario 1: text-only stream (the bread-and-butter case)
# ---------------------------------------------------------------------------
class TestStreamTextOnly:
  def test_no_tags_emits_full_text_and_no_dispatch(self):
    convo = Conversation(title="t")
    task = _task(convo)
    tokens: List[str] = []
    task.on(TaskEvent.TOKEN, lambda t: tokens.append(t))

    reg = _FakeToolRegistry(_stream("Hello, ", "world!"))
    SimpleAgent.execute(task, registry=reg)

    assert task.status == TaskStatus.COMPLETED
    assert task.result == "Hello, world!"
    assert "".join(tokens) == "Hello, world!"
    assert reg.execute_calls == []
    assert _utilities(convo) == []


# ---------------------------------------------------------------------------
# Scenario 2: streaming with one tool call
# ---------------------------------------------------------------------------
class TestStreamOneToolCall:
  def _registry_with_echo(self, chunks):
    def _echo(raw_payload, conversation, **kwargs):
      import json as _json
      data = _json.loads(raw_payload)
      params = data.get("parameters", data)
      return Result.ok(f"echoed:{params.get('message', '')}")

    return _FakeToolRegistry(chunks, tools={"demo.echo": _echo})

  def test_envelope_payload_dispatches_and_streams_result(self):
    convo = Conversation(title="t")
    task = _task(convo)
    tokens: List[str] = []
    task.on(TaskEvent.TOKEN, lambda t: tokens.append(t))

    chunks = _stream(
      'Calling tool now: ',
      '[TOOL_CALL]{"name": "demo.echo", "parameters": {"message": "hi"}}[/TOOL_CALL]',
      ' done.',
    )
    reg = self._registry_with_echo(chunks)

    SimpleAgent.execute(task, registry=reg)

    assert task.status == TaskStatus.COMPLETED

    # Dispatch happened with the qualified name and the verbatim payload.
    assert len(reg.execute_calls) == 1
    call = reg.execute_calls[0]
    assert call["qualified_name"] == "demo.echo"
    assert call["raw_payload"] == '{"name": "demo.echo", "parameters": {"message": "hi"}}'

    # The streaming message contains the model output AND the inline result.
    assistant_msg = _assistant_message(convo)
    assert "[TOOL_CALL]" in assistant_msg.content
    assert "echoed:hi" in assistant_msg.content

    # The ``token`` events include the result text (post-newline-prefix).
    assert "echoed:hi" in "".join(tokens)

    utilities = _utilities(convo)
    assert len(utilities) == 1
    assert utilities[0].tag_type is TagType.TOOL
    assert utilities[0].source_message_id == assistant_msg.message_id

  def test_bare_name_resolves_via_registry(self):
    convo = Conversation(title="t")
    task = _task(convo)
    reg = self._registry_with_echo(_stream(
      '[TOOL_CALL]{"name": "echo", "parameters": {"message": "yo"}}[/TOOL_CALL]',
    ))

    SimpleAgent.execute(task, registry=reg)
    assert task.status == TaskStatus.COMPLETED
    # Bare ``echo`` resolved to ``demo.echo``.
    assert reg.execute_calls[0]["qualified_name"] == "demo.echo"
    assert "echoed:yo" in _assistant_message(convo).content

  def test_tool_failure_surfaces_inline_error_text(self):
    convo = Conversation(title="t")
    task = _task(convo)
    # Envelope payload — ``decode_payload`` only surfaces ``name`` when
    # a sibling ``parameters`` key is present (see
    # ``test_simple_protocol_phase5.py``).
    reg = _FakeToolRegistry(
      _stream('[TOOL_CALL]{"name": "missing", "parameters": {}}[/TOOL_CALL]'),
      tools={},
    )

    SimpleAgent.execute(task, registry=reg)
    assert task.status == TaskStatus.COMPLETED
    content = _assistant_message(convo).content
    assert "[TOOL_ERROR]" in content
    assert "Tool not found" in content
    utilities = _utilities(convo)
    assert len(utilities) == 1
    assert utilities[0].tag_type is TagType.TOOL

  def test_payload_without_name_yields_typed_error(self):
    convo = Conversation(title="t")
    task = _task(convo)
    reg = self._registry_with_echo(_stream(
      '[TOOL_CALL]{"message": "no name here"}[/TOOL_CALL]',
    ))

    SimpleAgent.execute(task, registry=reg)
    assert task.status == TaskStatus.COMPLETED
    # No dispatch happened.
    assert reg.execute_calls == []
    content = _assistant_message(convo).content
    assert "[TOOL_ERROR]" in content
    assert "missing 'name'" in content


# ---------------------------------------------------------------------------
# Scenario 3: streaming with multiple tool calls
# ---------------------------------------------------------------------------
class TestStreamMultipleToolCalls:
  def test_two_tool_calls_dispatch_in_order(self):
    convo = Conversation(title="t")
    task = _task(convo)

    def _add(raw_payload, conversation, **kwargs):
      import json as _json
      data = _json.loads(raw_payload)
      params = data.get("parameters", {})
      return Result.ok(str(params["a"] + params["b"]))

    def _shout(raw_payload, conversation, **kwargs):
      import json as _json
      data = _json.loads(raw_payload)
      return Result.ok(data["parameters"]["msg"].upper())

    reg = _FakeToolRegistry(
      _stream(
        'sum=',
        '[TOOL_CALL]{"name": "math.add", "parameters": {"a": 2, "b": 3}}[/TOOL_CALL]',
        ' shout=',
        '[TOOL_CALL]{"name": "demo.shout", "parameters": {"msg": "hi"}}[/TOOL_CALL]',
        ' end.',
      ),
      tools={"math.add": _add, "demo.shout": _shout},
    )

    SimpleAgent.execute(task, registry=reg)
    assert task.status == TaskStatus.COMPLETED

    # Both calls fired in order.
    assert [c["qualified_name"] for c in reg.execute_calls] == ["math.add", "demo.shout"]

    content = _assistant_message(convo).content
    assert "5" in content
    assert "HI" in content

    utilities = _utilities(convo)
    assert len(utilities) == 2
    assert all(u.tag_type is TagType.TOOL for u in utilities)


# ---------------------------------------------------------------------------
# Scenario 4: thinking + tool call mixed
# ---------------------------------------------------------------------------
class TestStreamThinkingPlusTool:
  def test_thinking_recorded_as_utility_tool_dispatched(self):
    convo = Conversation(title="t")
    task = _task(convo)

    def _echo(raw_payload, conversation, **kwargs):
      return Result.ok("ok")

    reg = _FakeToolRegistry(
      _stream(
        '<think>Need to call the tool.</think>',
        ' Going.',
        '[TOOL_CALL]{"name": "demo.echo", "parameters": {}}[/TOOL_CALL]',
      ),
      tools={"demo.echo": _echo},
    )

    SimpleAgent.execute(task, registry=reg)
    assert task.status == TaskStatus.COMPLETED

    utilities = _utilities(convo)
    tag_types = sorted(u.tag_type.value for u in utilities)
    assert tag_types == ["thinking", "tool"]

    # Tool dispatched exactly once.
    assert len(reg.execute_calls) == 1
    assert reg.execute_calls[0]["qualified_name"] == "demo.echo"


# ---------------------------------------------------------------------------
# Tag content split across chunk boundaries
# ---------------------------------------------------------------------------
class TestStreamingChunkBoundaries:
  def test_open_close_split_across_chunks(self):
    """Sanity: the parser handles tag tokens that arrive split across
    chunk boundaries — the agent loop relies on the streaming
    semantics rather than a one-shot find-all pass."""
    convo = Conversation(title="t")
    task = _task(convo)

    def _ping(raw_payload, conversation, **kwargs):
      return Result.ok("pong")

    reg = _FakeToolRegistry(
      _stream(
        # Open token straddles two chunks.
        '[TOOL_',
        'CALL]{"name": "ping", "parameters": {}}[/TOO',
        'L_CALL]',
      ),
      tools={"demo.ping": _ping},  # qualified; agent resolves bare name
    )

    SimpleAgent.execute(task, registry=reg)
    assert task.status == TaskStatus.COMPLETED
    assert reg.execute_calls[0]["qualified_name"] == "demo.ping"
    assert "pong" in _assistant_message(convo).content


# ---------------------------------------------------------------------------
# Parser flush behavior
# ---------------------------------------------------------------------------
class TestParserFlush:
  def test_tool_call_at_end_of_stream_dispatches_on_flush(self):
    """If the close token is the very last bytes of the stream, the
    event might not fire until ``parser.flush()`` runs after the
    deployment loop ends."""
    convo = Conversation(title="t")
    task = _task(convo)

    def _ping(raw_payload, conversation, **kwargs):
      return Result.ok("pong")

    # Whole tag in a single chunk; nothing after it. Parser may emit
    # the event during ``feed`` (the close completes), but verify the
    # full pipeline regardless.
    reg = _FakeToolRegistry(
      _stream('[TOOL_CALL]{"name": "ping", "parameters": {}}[/TOOL_CALL]'),
      tools={"demo.ping": _ping},
    )
    SimpleAgent.execute(task, registry=reg)
    assert task.status == TaskStatus.COMPLETED
    assert len(reg.execute_calls) == 1


# ---------------------------------------------------------------------------
# Mismatched close (ParseError) is logged and ignored
# ---------------------------------------------------------------------------
class TestParseErrorTolerance:
  def test_unclosed_tag_does_not_crash_the_stream(self):
    convo = Conversation(title="t")
    task = _task(convo)
    reg = _FakeToolRegistry(_stream('hello [TOOL_CALL] never closes'))
    SimpleAgent.execute(task, registry=reg)
    # Task completes; the un-closed tag does not produce a utility
    # message and does not dispatch a tool call.
    assert task.status == TaskStatus.COMPLETED
    assert reg.execute_calls == []


# ---------------------------------------------------------------------------
# Registry.resolve_qualified_name unit tests
# ---------------------------------------------------------------------------
class TestRegistryResolveQualifiedName:
  def _registry_with_index(self, monkeypatch, qualified_names: List[str]):
    """Construct a real Registry whose tool index is pre-seeded with
    ``qualified_names`` (each pointing at a stub ``ToolReference``).
    The manager is stubbed to a no-op so this stays a pure unit test."""
    from claia.framework.manager import Manager as RealManager
    import claia.framework.registry as registry_module

    class _FakeManager:
      coerce_value = staticmethod(RealManager.coerce_value)
      filter_init_kwargs = staticmethod(RealManager.filter_init_kwargs)
      filter_runtime_kwargs = staticmethod(RealManager.filter_runtime_kwargs)
      resolve_runtime_kwargs = staticmethod(RealManager.resolve_runtime_kwargs)
      validate_required_init_kwargs = staticmethod(RealManager.validate_required_init_kwargs)
      _COERCE_FAIL = RealManager._COERCE_FAIL
      _mask_for_log = staticmethod(RealManager._mask_for_log)

      def discover_plugins(self): return None
      def load_all_plugins(self, **kwargs): return None
      def iter_protocol_instances(self): return iter(())

    monkeypatch.setattr(registry_module, "Manager", _FakeManager)
    reg = registry_module.Registry()
    reg._plugins_loaded = True
    reg._tool_index = {
      qn: ToolReference(qualified_name=qn, description="", protocol_name="simple")
      for qn in qualified_names
    }
    reg._protocols_by_name = {}
    return reg

  def test_already_qualified_name_returned_unchanged(self, monkeypatch):
    reg = self._registry_with_index(monkeypatch, ["mod.tool"])
    assert reg.resolve_qualified_name("mod.tool") == "mod.tool"

  def test_bare_name_resolves_to_qualified(self, monkeypatch):
    reg = self._registry_with_index(monkeypatch, ["mod.tool"])
    assert reg.resolve_qualified_name("tool") == "mod.tool"

  def test_unknown_name_returns_none(self, monkeypatch):
    reg = self._registry_with_index(monkeypatch, ["mod.tool"])
    assert reg.resolve_qualified_name("nothing") is None

  def test_multiple_matches_returns_first(self, monkeypatch):
    reg = self._registry_with_index(monkeypatch, ["alpha.tool", "beta.tool"])
    # Index dict ordering follows insertion (Python 3.7+).
    assert reg.resolve_qualified_name("tool") == "alpha.tool"


# ---------------------------------------------------------------------------
# Verify the legacy surface is gone
# ---------------------------------------------------------------------------
class TestLegacySurfaceRemoved:
  """``process_content`` and ``execute_legacy`` are gone."""

  def test_registry_no_longer_has_process_content(self):
    from claia.framework.registry import Registry
    assert not hasattr(Registry, "process_content")
    assert not hasattr(Registry, "contains_tool_tokens")
    assert not hasattr(Registry, "get_commands_catalog")

  def test_simple_protocol_no_longer_has_execute_legacy(self):
    from claia.core.tools.protocols.simple import SimpleProtocol
    assert not hasattr(SimpleProtocol, "execute_legacy")

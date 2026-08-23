"""Agent ToolMode gate: prompt, parser TOOL tags, and ToolChunk."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from claia.core.data import Conversation
from claia.core.data.chunks import BaseChunk, TextChunk, ToolChunk
from claia.core.enums.conversation import MessageRole
from claia.core.enums.parser import TagType
from claia.core.enums.task import TaskStatus
from claia.core.enums.tools import ToolMode
from claia.core.plugins.base import ToolReference
from claia.core.results import Result
from claia.framework.agents.simple import SimpleAgent
from claia.framework.task import Task


def _utilities(convo):
  return [m for m in convo.messages if m.role == MessageRole.UTILITY]


def _tool_results(convo):
  artifacts = []
  for utility in _utilities(convo):
    artifacts.extend(utility.tool_result_artifacts())
  return artifacts


class _FakeSolver:
  def __init__(self, supports_native: bool = False):
    self.supports_native = supports_native
    self.calls = 0

  def solve(self, model_name, deployment_preference="any"):
    self.calls += 1
    return SimpleNamespace(supports_native_tools=self.supports_native)


class _FakeRegistry:
  def __init__(
    self,
    chunks: List[BaseChunk],
    tools: Optional[Dict[str, Any]] = None,
    follow_ups: Optional[List[List[BaseChunk]]] = None,
    supports_native: bool = False,
  ):
    self._runs: List[List[BaseChunk]] = [list(chunks)]
    if follow_ups:
      self._runs.extend(list(run) for run in follow_ups)
    self._tools: Dict[str, Any] = tools or {}
    self.execute_calls: List[Dict[str, Any]] = []
    self.run_calls = 0
    self.systems: List[Optional[str]] = []
    self.run_tools: List[Any] = []
    self.solver = _FakeSolver(supports_native)
    self.solutions: List[Any] = []

  def run(self, model_id, conversation, streaming=False, solution=None, **kwargs):
    assert streaming is True
    self.run_calls += 1
    self.systems.append(kwargs.get("system"))
    self.run_tools.append(kwargs.get("tools"))
    self.solutions.append(solution)
    if self._runs:
      chunks = self._runs.pop(0)
    else:
      chunks = []
    return iter(chunks)

  def get_supported_models(self):
    return {}

  def list_tools(self):
    return [
      ToolReference(
        qualified_name="demo.echo",
        description="Echo back the provided message",
        protocol_name="simple",
      )
    ]

  def resolve_qualified_name(self, name: str) -> Optional[str]:
    if name in self._tools:
      return name
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


def _echo_tools():
  def _echo(raw_payload, conversation, **kwargs):
    return Result.ok("echoed:hi")
  return {"demo.echo": _echo}


def _task(conversation, **parameters):
  params = {"model_id": "dummy-model"}
  params.update(parameters)
  return Task(conversation=conversation, parameters=params)


def test_manual_prepends_tool_prompt():
  convo = Conversation(title="t")
  task = _task(convo)
  reg = _FakeRegistry([TextChunk(data="hello")])
  SimpleAgent.execute(task, registry=reg)

  assert task.status == TaskStatus.COMPLETED
  assert reg.systems[0].startswith("You can call tools")
  assert "demo.echo" in reg.systems[0]
  assert reg.run_tools[0] is None
  assert reg.solver.calls == 1
  assert reg.solutions[0] is not None


def test_native_skips_tool_prompt_when_outputs_list_toolchunk():
  convo = Conversation(title="t")
  task = _task(convo, tool_mode=ToolMode.NATIVE, system="You write poetry.")
  reg = _FakeRegistry([TextChunk(data="hello")], supports_native=True)
  SimpleAgent.execute(task, registry=reg)

  assert task.status == TaskStatus.COMPLETED
  assert reg.systems[0] == "You write poetry."
  assert "You can call tools" not in reg.systems[0]
  assert [ref.qualified_name for ref in reg.run_tools[0]] == ["demo.echo"]


def test_native_parser_tool_tags_are_ignored():
  convo = Conversation(title="t")
  task = _task(convo, tool_mode=ToolMode.NATIVE)
  reg = _FakeRegistry(
    [
      TextChunk(data='<think>planning</think>'),
      TextChunk(data='[TOOL_CALL]{"name": "demo.echo", "parameters": {"message": "hi"}}[/TOOL_CALL]'),
    ],
    tools=_echo_tools(),
    supports_native=True,
  )
  SimpleAgent.execute(task, registry=reg)

  assert task.status == TaskStatus.COMPLETED
  assert reg.execute_calls == []
  utilities = _utilities(convo)
  assert [u.tag_type for u in utilities] == [TagType.THINKING]
  assert _tool_results(convo) == []


def test_native_tool_chunk_dispatches_and_continues():
  convo = Conversation(title="t")
  task = _task(convo, tool_mode=ToolMode.NATIVE)
  chunk = ToolChunk(tool_name="demo.echo", payload={"message": "hi"}, call_id="c1")
  reg = _FakeRegistry(
    [chunk],
    tools=_echo_tools(),
    follow_ups=[[TextChunk(data="The tool said hi.")]],
    supports_native=True,
  )
  SimpleAgent.execute(task, registry=reg)

  assert task.status == TaskStatus.COMPLETED
  assert task.result == "The tool said hi."
  assert reg.run_calls == 2
  assert reg.solver.calls == 2
  assert len(reg.execute_calls) == 1
  assert reg.execute_calls[0]["qualified_name"] == "demo.echo"
  assert '"name": "demo.echo"' in reg.execute_calls[0]["raw_payload"]
  assert "tool_mode" not in reg.execute_calls[0]["kwargs"]

  results = _tool_results(convo)
  assert len(results) == 1
  assert results[0].tool_name == "demo.echo"
  assert results[0].content == "echoed:hi"
  assert results[0].call_id == "c1"
  utilities = _utilities(convo)
  assert len(utilities) == 1
  assert utilities[0].tag_type is TagType.TOOL


def test_manual_ignores_tool_chunk():
  convo = Conversation(title="t")
  task = _task(convo)
  reg = _FakeRegistry(
    [ToolChunk(tool_name="demo.echo", payload={"message": "hi"})],
    tools=_echo_tools(),
    supports_native=True,
  )
  SimpleAgent.execute(task, registry=reg)

  assert task.status == TaskStatus.COMPLETED
  assert reg.execute_calls == []
  assert _utilities(convo) == []
  assert _tool_results(convo) == []


def test_native_request_without_toolchunk_stays_manual():
  convo = Conversation(title="t")
  task = _task(convo, tool_mode=ToolMode.NATIVE, system="You write poetry.")
  reg = _FakeRegistry([TextChunk(data="hello")], supports_native=False)
  SimpleAgent.execute(task, registry=reg)

  assert task.status == TaskStatus.COMPLETED
  assert reg.systems[0].startswith("You can call tools")
  assert reg.systems[0].endswith("You write poetry.")
  assert reg.run_tools[0] is None

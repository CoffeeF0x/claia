"""Sanity: watch the BaseAgent tool loop against a real Registry.

Only ``Registry.run`` is stubbed (scripted assistant turns, no LLM).
Tool inventory, parse, and ``execute_tool`` go through the live
simple protocol + sample module.

    PYTHONPATH=src python -m sanity.tool_loop
"""

from claia.core.data import Conversation
from claia.core.data.chunks import TextChunk
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.enums.conversation import MessageRole
from claia.framework.agents.base import BaseAgent
from claia.framework.registry import Registry
from claia.framework.task import Task


PERSONA = "Stay terse. Use tools when they help."
USER_REQUEST = "Echo the word hello, then add 2 and 3."


class ScriptedRegistry(Registry):
  """Real registry; ``run`` plays back scripted assistant text."""

  def __init__(self, *streams):
    super().__init__()
    self.load_plugins()
    self._streams = [list(s) for s in streams]
    self.snapshots = []
    self.last_system = ""

  def run(self, model_id, conversation, streaming=False, system=None, **kwargs):
    self.last_system = system or ""
    self.snapshots.append({
      "round": len(self.snapshots) + 1,
      "inputs": conversation.to_model_inputs(
        definition=ModelDefinition(),
        system=system,
      ),
    })
    chunks = self._streams.pop(0) if self._streams else []
    return iter(chunks)


def _stream(*texts):
  return [TextChunk(data=t) for t in texts]


def _format_inputs(sequence) -> str:
  lines = []
  for message in sequence.messages:
    lines.append(f"--- {message.role.value} ---")
    lines.append(message.content)
    lines.append("")
  return "\n".join(lines).rstrip()


def _format_tree(conversation: Conversation) -> str:
  lines = []
  for message in conversation.messages:
    extra = ""
    if message.role is MessageRole.UTILITY and message.tag_type is not None:
      extra = f" tag_type={message.tag_type.value}"
    lines.append(f"--- {message.role.value}{extra} ---")
    lines.append(message.content)
    lines.append("")
  return "\n".join(lines).rstrip()


def run_loop():
  registry = ScriptedRegistry(
    _stream(
      "I'll echo first.\n",
      '[TOOL_CALL]{"name": "sample.echo", "parameters": {"message": "hello"}}[/TOOL_CALL]',
    ),
    _stream(
      "Now the sum.\n",
      '[TOOL_CALL]{"name": "sample.add", "parameters": {"a": 2, "b": 3}}[/TOOL_CALL]',
    ),
    _stream("hello, and 2 + 3 = 5."),
  )

  print("registry tools:")
  for ref in registry.list_tools():
    print(f"  {ref.qualified_name}  ({ref.protocol_name})")
  print()

  convo = Conversation(title="sanity-tool-loop")
  convo.add_message(MessageRole.USER, USER_REQUEST)
  task = Task(
    conversation=convo,
    parameters={"model_id": "dummy-model", "system": PERSONA},
  )
  BaseAgent.execute(task, registry=registry)

  print("======== SYSTEM (every generate) ========")
  print(registry.last_system)
  print()
  for snap in registry.snapshots:
    print(f"======== GENERATE {snap['round']} — model sees ========")
    print(_format_inputs(snap["inputs"]))
    print()
  print("======== FINAL VISIBLE THREAD (utilities stripped) ========")
  print(_format_inputs(convo.to_model_inputs(definition=ModelDefinition())))
  print()
  print("======== FULL TREE (includes utilities) ========")
  print(_format_tree(convo))
  print()


if __name__ == "__main__":
  print("Starting...")
  run_loop()

"""
Base architecture abstract class.

An architecture owns the inference protocol for a model family:
input formatting, talking to the served model, parsing output, and
the family's feature surface. Contract: model inputs in (a
``MessageSequence`` or artifact list), ``ModelResponse`` out.
Implementations may yield ``BaseChunk`` items while streaming and
return the filled ``ModelResponse`` via the generator's return value.

Each architecture declares the deployment that serves it through the
``deployment`` class attribute (e.g. ``"api"``, ``"transformers"``);
the solver follows that link when resolving a model call.
"""

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Generator, List, Sequence, Union

from ...data.artifacts import BaseArtifact, ToolArtifact
from ...data.chunks import BaseChunk
from ...data.models.conversation.message_sequence import MessageSequence
from ...data.response import ModelResponse
from ...enums.conversation import MessageRole


ModelInputs = Union[MessageSequence, Sequence[BaseArtifact], BaseArtifact, List[BaseArtifact]]


########################################################################
#                              CLASSES                                 #
########################################################################
class BaseArchitecture(ABC):
  """Abstract base class for all architecture implementations."""

  #: Name of the deployment plugin that serves this architecture.
  deployment: ClassVar[str] = ""

  def __init__(self, model_name: str):
    self.model_name = model_name

  def format_messages(self, sequence: MessageSequence) -> List[Dict[str, str]]:
    """Default MANUAL presentation of a message sequence.

    User and assistant text pass through. Tool-result utilities become
    user turns carrying ``[TOOL_RESULT]`` blocks. ``SYSTEM`` turns are
    omitted — callers use ``sequence.system``. Architectures that need
    a different wire shape override this.
    """
    formatted: List[Dict[str, str]] = []
    for message in sequence.messages:
      role = message.role
      if role == MessageRole.SYSTEM:
        continue
      if role == MessageRole.UTILITY:
        text = self.format_tool_utility(message)
        if text:
          formatted.append({"role": "user", "content": text})
        continue
      if role in (MessageRole.USER, MessageRole.ASSISTANT) and message.content:
        formatted.append({"role": role.value, "content": message.content})
    return formatted

  def format_tool_utility(self, message) -> str:
    """Render a utility turn's tool-result artifacts as MANUAL text."""
    blocks = [
      artifact.result_text()
      for artifact in getattr(message, "artifacts", []) or []
      if isinstance(artifact, ToolArtifact) and artifact.is_result
    ]
    return "\n\n".join(blocks)

  @staticmethod
  def format_tool_result(name: str, body: str) -> str:
    """Default MANUAL-mode presentation of a tool result."""
    return ToolArtifact.format_result(name, body)

  @staticmethod
  def coalesce_consecutive_roles(
    messages: List[Dict[str, str]],
  ) -> List[Dict[str, str]]:
    """Merge adjacent same-role text turns.

    For provider APIs that require strict user/assistant alternation
    after utilities have been mapped to user turns.
    """
    if not messages:
      return []
    merged: List[Dict[str, str]] = [dict(messages[0])]
    for message in messages[1:]:
      if message.get("role") == merged[-1].get("role"):
        prev = merged[-1].get("content") or ""
        nxt = message.get("content") or ""
        merged[-1]["content"] = (prev + "\n" + nxt).strip()
      else:
        merged.append(dict(message))
    return merged

  @abstractmethod
  def generate(
    self,
    inputs: ModelInputs,
    **kwargs,
  ) -> Union[ModelResponse, Generator[BaseChunk, None, ModelResponse]]:
    """Generate a response from model inputs.

    ``inputs`` is either a ``MessageSequence`` / ``MessageSequenceOrdered``
    or a list of artifacts (possibly empty). Prefer returning a
    ``ModelResponse`` directly; streaming implementations may yield
    chunks and ``return`` a ``ModelResponse``.

    Failure rule: raise when the request cannot start (bad inputs,
    connection refused, provider rejects the request outright); once
    content has streamed, finish with ``ModelResponse.error`` set and
    ``complete=False`` instead. Errors are never chunk content.
    """
    pass

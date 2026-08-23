"""
Agent request — the object that travels the serving pipeline.

The registry builds one ``AgentRequest`` after solve and ParamSpec
filtering. Each layer reads the fields it needs. Inputs are already
translated (``MessageSequence`` or artifact list); the Conversation
does not ride on the request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Type, Union

from .artifacts import BaseArtifact
from .models.conversation.message_sequence import MessageSequence


ModelInputs = Union[
  MessageSequence,
  Sequence[BaseArtifact],
  BaseArtifact,
  List[BaseArtifact],
]


@dataclass
class AgentRequest:
  """One generate call traveling the serving pipeline.

  Attributes:
    model: Canonical model name from solve.
    provider_model: Identifier handed to the architecture.
    architecture_class: Architecture type to deploy or reuse.
    deployment: Deployment that serves the architecture.
    inputs: Translated model inputs (sequence or artifacts).
    init_args: INIT-scope kwargs for ``deploy``.
    args: RUNTIME-scope kwargs for ``generate`` (tools, stream, …).
    data: Freeform extras (host or request metadata).
  """

  model: str
  provider_model: str
  architecture_class: Type
  deployment: Any
  inputs: ModelInputs
  init_args: Dict[str, Any] = field(default_factory=dict)
  args: Dict[str, Any] = field(default_factory=dict)
  data: Dict[str, Any] = field(default_factory=dict)

"""How a model expects conversation turns to be shaped."""

from enum import Enum


class SequenceKind(Enum):
  """Message-sequence mode declared on a ``ModelDefinition``."""

  NONE = "none"
  """No multi-turn sequence — typically a single flattened turn."""

  MESSAGE = "message"
  """Ordered active-thread messages filtered to supported artifacts."""

  ORDERED = "ordered"
  """Like MESSAGE, but role-alternation enforced (e.g. Anthropic)."""

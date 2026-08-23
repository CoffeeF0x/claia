from enum import Enum


class ToolMode(Enum):
  """Who owns tool calling for a model run.

  The agent still runs the tag-parser pass every turn. This value
  decides whether those parsed calls are used and stored, and whether
  the agent prepends the MANUAL tool-calling prompt.

  ``NATIVE`` — the architecture / provider implements tool calling.
  Parsed tags are ignored (not dispatched, not stored). Used only
  when requested and the solved definition lists ``ToolChunk``.
  ``MANUAL`` — framework-owned tag parsing. Parsed calls are
  dispatched, stored as tool utilities, and the agent injects the
  tool-calling instructions.
  """
  NATIVE = "native"
  MANUAL = "manual"

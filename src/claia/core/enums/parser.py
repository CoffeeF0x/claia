from enum import Enum


class TagType(Enum):
  """Categorical kind of a parsed tag span.

  The set is intentionally small at the start; new categories are
  added as new tag-shaped artifacts are introduced (e.g., a future
  ``CODE`` for opaque code blocks). The string value is stable and
  used for serialization / persistence of utility messages.
  """
  TOOL = "tool"
  THINKING = "thinking"
  REFERENCE = "reference"

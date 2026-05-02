"""
Tag-spec resolution from a model definition.

Each ``ModelDefinition`` may declare a ``tag_overrides`` mapping
that swaps the default ``TagSpec`` for one or more ``TagType`` values.
``resolve_tag_specs`` returns the merged list of specs for that model
in a form ready to feed into ``StreamingTagParser``.

Per-tag-type replacement: if a model overrides ``TagType.TOOL`` it
provides a complete ``TagSpec``; there is no field-level merging.

The ``tag_overrides`` field on ``ModelDefinition`` is added in Phase
2 of the tools-overhaul plan. This helper reads the field defensively
via ``getattr`` so it can be exercised before the field lands.
"""

from typing import Any, Dict, List, Optional

from .defaults import DEFAULT_TAGS
from .types import TagSpec, TagType


########################################################################
#                          SPEC RESOLUTION                             #
########################################################################
def resolve_tag_specs(model_def: Any) -> List[TagSpec]:
  """Resolve the active ``TagSpec`` list for a given model definition.

  Args:
    model_def: A ``ModelDefinition`` (or any object exposing an
      optional ``tag_overrides`` attribute mapping
      ``TagType -> TagSpec``). ``None`` is accepted and returns the
      defaults.

  Returns:
    A list of ``TagSpec`` with one entry per ``TagType`` covered by
    the defaults plus any overrides that introduce additional tag
    types.
  """
  merged: Dict[TagType, TagSpec] = dict(DEFAULT_TAGS)
  overrides: Optional[Dict[TagType, TagSpec]] = (
    getattr(model_def, "tag_overrides", None) if model_def is not None else None
  )
  if overrides:
    merged.update(overrides)
  return list(merged.values())

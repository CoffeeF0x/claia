"""
Tag-spec resolution from a model definition.

Each ``ModelDefinition`` may declare a ``tag_overrides`` mapping
that swaps the default ``TagSpec`` for one or more ``TagType`` values.
``resolve_tag_specs`` returns the merged list of specs for that model
in a form ready to feed into ``TagParser``.

Per-tag-type replacement: if a model overrides ``TagType.TOOL`` it
provides a complete ``TagSpec``; there is no field-level merging.

The lookup of ``tag_overrides`` uses ``getattr`` with a ``None``
default so this helper accepts any duck-typed object — concrete
``ModelDefinition`` instances, lightweight test stand-ins, or
``None`` itself when no model definition is available.
"""

from typing import Any, Dict, List, Optional

from ..enums.parser import TagType
from .defaults import DEFAULT_TAGS
from .types import TagSpec


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
    the defaults, plus any overrides that introduce additional tag
    types. Default entries whose ``TagType`` appear in the overrides
    are replaced; entries not present in the overrides are
    preserved verbatim.
  """
  merged: Dict[TagType, TagSpec] = dict(DEFAULT_TAGS)
  overrides: Optional[Dict[TagType, TagSpec]] = (
    getattr(model_def, "tag_overrides", None) if model_def is not None else None
  )
  if overrides:
    merged.update(overrides)
  return list(merged.values())

"""
Legacy tool-protocol ABC (pre-overhaul contract).

Kept importable so third-party code that extended the pre-overhaul
``BaseProtocol`` surface can still import it during the transition. A
``DeprecationWarning`` fires at import time and again on subclass
creation so downstream authors know to migrate to the new
``claia.core.tools.protocols.base.BaseProtocol`` contract (see
``docs/tools-overhaul-plan.md`` §6).

No CLAIA code should depend on this module — the in-tree
``SimpleProtocolPlugin`` implements the new contract directly. This
module exists only as a deprecation-banner landing pad for external
extensions.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict

from ...results import Result
from ...plugins.base import ProtocolInfo


warnings.warn(
  "claia.core.tools.protocols._legacy.LegacyBaseProtocol is deprecated. "
  "Migrate to claia.core.tools.protocols.base.BaseProtocol; see "
  "docs/tools-overhaul-plan.md §6 for the new contract.",
  DeprecationWarning,
  stacklevel=2,
)


class LegacyBaseProtocol(ABC):
  """Pre-overhaul contract for tool-protocol plugins.

  The new contract (see ``claia.core.tools.protocols.base``) inverts
  tool-inventory ownership — protocols now surface their own
  ``ToolReference`` list via ``get_tool_references()`` instead of
  receiving a ``commands`` catalog at execute time. This class is kept
  only so legacy imports keep working; subclassing it triggers another
  ``DeprecationWarning`` at class-creation time.
  """

  info: ClassVar[ProtocolInfo]

  def __init_subclass__(cls, **kwargs: Any) -> None:
    super().__init_subclass__(**kwargs)
    warnings.warn(
      f"{cls.__module__}.{cls.__name__} subclasses the deprecated "
      "LegacyBaseProtocol. Migrate to "
      "claia.core.tools.protocols.base.BaseProtocol.",
      DeprecationWarning,
      stacklevel=2,
    )

  def get_protocol_info(self) -> ProtocolInfo:
    """Return metadata describing this protocol."""
    return type(self).info

  @abstractmethod
  def execute(
    self,
    tool_name: str,
    parameters: Dict[str, Any],
    conversation,
    commands: Dict[str, Any],
    **kwargs,
  ) -> Result:
    """Execute ``tool_name`` and return a ``Result`` (legacy signature)."""


__all__ = ["LegacyBaseProtocol"]

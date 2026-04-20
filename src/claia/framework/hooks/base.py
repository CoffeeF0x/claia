"""
Re-export of ``ExtensionInfo`` for the framework's hookspec wrappers.

The dataclass itself lives in ``claia.core.plugins.base``; this module
provides a stable import path inside the framework (``claia.hooks.base``)
for backwards compatibility and so the hookspec modules can pull it from
a single place.
"""

from claia.core.plugins.base import ExtensionInfo

__all__ = ["ExtensionInfo"]

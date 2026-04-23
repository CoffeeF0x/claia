"""
Re-export of ``ExtensionInfo`` for the framework's hookspec wrappers.

The dataclass itself lives in ``claia.core.plugins.base``; this module
gives the hookspec modules under ``claia.framework.hooks`` a single
in-framework import path so they don't each have to reach across
packages.
"""

from claia.core.plugins.base import ExtensionInfo

__all__ = ["ExtensionInfo"]

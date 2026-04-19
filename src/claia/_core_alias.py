"""
Import alias: route ``claia.core[.X...]`` to ``claia_core[.X...]``.

This module installs a meta-path finder so that any ``import claia.core.X``
or ``from claia.core.X import Y`` resolves to the *same module object* as the
corresponding ``claia_core.X`` import. Without this hook, Python would import
each ``claia.core.X`` submodule a second time as a distinct module object,
which would break ``isinstance`` checks, double-execute module-level code,
and create silent class-identity bugs.

The framework's ``__init__.py`` imports this module so the finder is
registered before any user code can ``import claia.core...``. The finder is
a no-op for any name that does not start with ``claia.core``.

Standalone ``import claia_core[.X]`` continues to work exactly as before;
this hook only ever *adds* a second valid name for the same module objects.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
from typing import Sequence

_ALIAS_ROOT = "claia.core"
_TARGET_ROOT = "claia_core"


def _alias_to_target(fullname: str) -> str:
  """Map ``claia.core[.tail]`` to ``claia_core[.tail]``."""
  if fullname == _ALIAS_ROOT:
    return _TARGET_ROOT
  return _TARGET_ROOT + fullname[len(_ALIAS_ROOT):]


class _ClaiaCoreAliasLoader(importlib.abc.Loader):
  """Loader that returns a pre-imported module instead of executing one."""

  def __init__(self, real_module):
    self._real_module = real_module

  def create_module(self, spec):
    return self._real_module

  def exec_module(self, module):
    # The real module was already executed when we imported it.
    return None


class _ClaiaCoreAliasFinder(importlib.abc.MetaPathFinder):
  """Meta-path finder that aliases ``claia.core.*`` onto ``claia_core.*``."""

  def find_spec(self, fullname: str, path: Sequence[str] | None, target=None):
    if fullname != _ALIAS_ROOT and not fullname.startswith(_ALIAS_ROOT + "."):
      return None

    target_name = _alias_to_target(fullname)
    try:
      real_module = importlib.import_module(target_name)
    except ImportError:
      return None

    sys.modules[fullname] = real_module
    spec = importlib.machinery.ModuleSpec(
      name=fullname,
      loader=_ClaiaCoreAliasLoader(real_module),
      is_package=hasattr(real_module, "__path__"),
    )
    if hasattr(real_module, "__path__"):
      spec.submodule_search_locations = list(real_module.__path__)
    return spec


def _install() -> None:
  """Idempotently install the alias finder at the front of sys.meta_path."""
  for finder in sys.meta_path:
    if isinstance(finder, _ClaiaCoreAliasFinder):
      return
  sys.meta_path.insert(0, _ClaiaCoreAliasFinder())


_install()

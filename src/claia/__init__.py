"""
claia — the CLAIA framework.

Provides the inversion-of-control runtime on top of ``claia_core``:

- ``Manager`` discovers plugins via pluggy entry points (architectures,
  deployments, solvers, definitions, tool patterns/protocols/modules,
  agents).
- ``Registry`` is the application-facing composition root that
  orchestrates models, tools, and agents.
- ``Process`` and ``ProcessQueue`` model units of work; worker threads
  spawned by the registry consume them.
- ``BaseAgent`` and the ``simple`` agent live under ``claia.agents``.

Quick library example::

    from claia import Registry, Conversation

    registry = Registry()
    registry.load_plugins(openai_api_token="sk-...")
    registry.start_workers(2)

    conv = Conversation()
    conv.add_message_from_role("user", "Hello!")
    result = registry.run("gpt-4", conv)
    print(result.get_data())

Streaming::

    for token in registry.run("gpt-4", conv, streaming=True):
        print(token, end="", flush=True)

Callback-style query::

    result = registry.query(
        "gpt-4", "Hello!",
        on_token=lambda t: print(t, end="", flush=True),
    )
"""

# Expose the pure-library layer as ``claia.core`` so callers can write
# ``from claia import core`` and ``core.data.Conversation`` without having
# to reach for the ``claia_core`` distribution name directly. The two are
# the same module object.
import sys as _sys
import claia_core
core = claia_core
_sys.modules[__name__ + ".core"] = claia_core

# Convenience re-exports from the core layer so ``from claia import ...``
# keeps working for the most common types.
from claia_core.results import Result, DeploymentError
from claia_core.data import Conversation

# Framework primitives
from .process import Process
from .queue import ProcessQueue
from .registry import Registry
from .agents.base import BaseAgent

__all__ = [
    "core",
    "Registry",
    "Process",
    "ProcessQueue",
    "BaseAgent",
    "Result",
    "DeploymentError",
    "Conversation",
]

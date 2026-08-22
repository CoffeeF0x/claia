"""
SimpleProtocol package — bridges native ``BaseToolModule``
plugins into the post-overhaul ``BaseProtocol`` contract.

Public surface is :class:`SimpleProtocol`. Internals are split
across three modules:

- ``protocol.py``   — the ``BaseProtocol`` implementation.
- ``dispatcher.py`` — kwargs preparation, type coercion, callable
  resolution; consumed by ``protocol.py`` and reused by
  ``Registry.run_command`` for the CLI direct-execution path.
- ``payload.py``    — ``raw_payload`` (JSON) decoding into
  ``(parameters, name_hint)`` tuples.

The ``simple = "claia.core.tools.protocols.simple:SimpleProtocol"``
entry point continues to resolve here because the package re-exports
the class at module level.
"""

from .protocol import SimpleProtocol

__all__ = ["SimpleProtocol"]

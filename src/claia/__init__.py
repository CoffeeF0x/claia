"""
CLAIA AI Assistant Framework

A flexible framework for building AI assistants with pluggable architectures,
deployments, and agents.

Library usage::

    from claia import Registry, Conversation, Process, Result

    registry = Registry()
    registry.load_plugins(openai_api_token="sk-...")
    registry.start_workers(2)

    # One-shot (blocking, no streaming)
    conv = Conversation()
    conv.add_message_from_role("user", "Hello!")
    result = registry.run_sync("gpt-4", conv)
    print(result.get_data())

    # Streaming via callbacks
    result = registry.query("gpt-4", "Hello!",
        on_token=lambda t: print(t, end="", flush=True))
"""

from .registry import Registry
from .lib.results import Result
from .lib.process import Process
from .lib.data import Conversation

__all__ = [
  "Registry",
  "Result",
  "Process",
  "Conversation",
]

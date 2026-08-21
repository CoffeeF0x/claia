"""
Framework-side plugin decorators.

``agent`` lives here because ``AgentInfo`` / ``BaseAgent`` are
framework types and ``claia.core`` never imports the framework.
Decorated agents are recorded into the same collection
``claia.core.decorators`` exposes for manifest discovery, and leave
``agent_class`` unset — the manager fills it at discovery exactly as
it does for a hand-written ``info``.
"""

from ..core.decorators import PluginDecorator
from .agents.base import AgentInfo


########################################################################
#                           KIND INSTANCES                             #
########################################################################
agent = PluginDecorator(AgentInfo, "claia.agents", label="agent")


__all__ = ["agent"]

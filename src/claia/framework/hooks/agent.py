"""
Pluggy hookspecs for agent plugins.

Agents are framework-level: they orchestrate calls through the
``Registry`` and live in ``claia.agents``. ``AgentInfo`` therefore lives
here in the framework rather than in ``claia.core.plugins.base`` — its
``agent_class`` field references ``claia.agents.base.BaseAgent``.
"""

import pluggy
from dataclasses import dataclass, field
from typing import Optional, Type

from claia.core.plugins.base import ExtensionInfo
from claia.framework.agents.base import BaseAgent


@dataclass
class AgentInfo(ExtensionInfo):
  """Information about an agent implementation.

  Extends ``ExtensionInfo`` with the concrete ``agent_class`` to
  instantiate. Agents are registered programmatically (see
  ``Registry.register``) or via the ``claia.agents`` entry-point group.
  """
  agent_class: Optional[Type[BaseAgent]] = field(default=None)


hookspec = pluggy.HookspecMarker("claia_agents")


class AgentHooks:
  """Hook specifications for agent plugins."""

  @hookspec
  def get_agent_class(self, agent_name: str) -> Type[BaseAgent]:
    """Return the agent class for a given ``agent_name`` (or None)."""

  @hookspec
  def get_agent_info(self) -> AgentInfo:
    """Return metadata describing this agent."""


__all__ = ["AgentHooks", "AgentInfo"]

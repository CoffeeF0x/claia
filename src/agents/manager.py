"""
Agent manager for the CLAIA agents system.

This module handles loading and coordinating agent plugins using pluggy.
"""

import pluggy
import logging
import importlib.metadata as metadata
from typing import Optional, Dict, List, Type, Any

# Internal dependencies
from .hooks import AgentHooks, AgentInfo
from .lib import BaseAgent



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class AgentManager:
  """
  Manages agent plugins for the CLAIA agent system.

  This class coordinates agent plugins that implement specific agent behaviors.
  """

  def __init__(self):
    """Initialize the agent manager."""
    # Create plugin manager for agent plugins
    self.agent_pm = pluggy.PluginManager("claia_agents")
    self.agent_pm.add_hookspecs(AgentHooks)

    self._plugins_loaded = False

    logger.debug("AgentManager initialized")

  def load_all_plugins(self) -> None:
    """Load all agent plugins from entry points."""
    if self._plugins_loaded:
      return

    try:
      # Load plugins dynamically from entry points
      self._load_agent_plugins()

      self._plugins_loaded = True
      logger.info("All agent plugins loaded successfully")

    except Exception as e:
      logger.error(f"Error loading agent plugins: {e}")
      raise RuntimeError(f"Failed to load agent plugins: {e}")

  def _load_agent_plugins(self) -> None:
    """Load agent plugins from entry points."""
    loaded_count = 0

    try:
      # Load plugins from entry points
      for entry_point in metadata.entry_points().select(group='claia.agents'):
        try:
          plugin_class = entry_point.load()
          plugin_instance = plugin_class()
          self.agent_pm.register(plugin_instance)
          loaded_count += 1
          logger.debug(f"Loaded agent plugin: {entry_point.name} from {entry_point.value}")
        except Exception as e:
          logger.warning(f"Failed to load agent plugin {entry_point.name}: {e}")

      if loaded_count == 0:
        logger.warning("No agent plugins found in entry points, using built-in agents")

      logger.info(f"Loaded {loaded_count} agent plugins from entry points")

    except Exception as e:
      logger.error(f"Error loading agent plugins from entry points: {e}")
      raise

  def get_agent_class(self, agent_name: str) -> Optional[Type[BaseAgent]]:
    """
    Get the agent class for a specific agent name.

    Args:
        agent_name: The name of the agent to get the class for

    Returns:
        The agent class that can handle the specified agent type, or None if not found
    """
    self.load_all_plugins()

    # Query all plugins for the agent class
    results = self.agent_pm.hook.get_agent_class(agent_name=agent_name)

    for result in results:
      if result is not None:
        logger.debug(f"Found agent class {result.__name__} for {agent_name}")
        return result

    logger.debug(f"No agent class found for {agent_name}")
    return None

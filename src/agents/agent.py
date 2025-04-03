"""
This module contains the Agent class for CLAIA agent system.
The Agent class is the entry point for processing requests.

The Agent class is implemented as a singleton, which means there is only
one instance of it throughout the application. It can be accessed using
the class methods directly (preferred) or by calling Agent.get_instance().

Examples:
    # Using class methods directly (preferred)
    Agent.register_agent("custom", CustomAgent)
    result = Agent.process(process)
    agent_types = Agent.get_agent_types()

    # Using the singleton instance (alternative)
    agent = Agent.get_instance()
    agent_types = agent.get_agent_types()  # Note: Instance methods use the class methods
"""

# External dependencies
import logging
from typing import List, Dict, Any, Type, Optional

# Internal dependencies
from .process import Process
from .simple import SimpleAgent



########################################################################
#                              CONSTANTS                               #
########################################################################
DEFAULT_AGENT_TYPE = "simple"



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               AGENT                                  #
########################################################################
class Agent:
  """
  Agent class that serves as the entry point for processing requests.

  This class dispatches process requests to the appropriate agent implementation
  based on the process's agent_type.

  This class is implemented as a singleton.
  """
  # Singleton instance
  _instance: Optional['Agent'] = None

  # Registry to store agent implementations
  _agent_registry: Dict[str, Type] = {}

  def __new__(cls):
    """
    Create a new instance of Agent if one doesn't exist yet.

    Returns:
        The singleton instance of Agent
    """
    if cls._instance is None:
      cls._instance = super(Agent, cls).__new__(cls)
      # Initialize any instance attributes here
    return cls._instance

  def __init__(self):
    """
    Initialize the Agent singleton if it hasn't been initialized.
    """
    # No initialization needed as registry is a class variable
    pass

  @classmethod
  def register_agent(cls, agent_type: str, agent_class: Type):
    """
    Register an agent implementation for a specific agent type.

    Args:
        agent_type: The type of agent to register (string)
        agent_class: The agent class implementation
    """
    # Convert agent_type to lowercase for case-insensitive matching
    agent_type = agent_type.lower()
    cls._agent_registry[agent_type] = agent_class
    logger.debug(f"Registered agent {agent_class.__name__} for type {agent_type}")

  @classmethod
  def get_agent_for_type(cls, agent_type: str):
    """
    Get the agent implementation for a specific agent type.

    Args:
        agent_type: The type of agent to get (string)

    Returns:
        The agent class for the specified type, or SimpleAgent if not found
    """
    # If agent_type is None, use the default
    if agent_type is None:
      logger.debug(f"No agent type specified, using default: {cls.DEFAULT_AGENT_TYPE}")
      agent_type = cls.DEFAULT_AGENT_TYPE

    # Convert to lowercase for case-insensitive matching
    agent_type_lower = agent_type.lower() if isinstance(agent_type, str) else ""

    agent_class = cls._agent_registry.get(agent_type_lower)
    if not agent_class:
      logger.warning(f"No agent registered for type '{agent_type}', using SimpleAgent")
      return SimpleAgent
    return agent_class

  @classmethod
  def get_agent_types(cls) -> List[Dict[str, Any]]:
    """
    Get a list of all available agent types with descriptions.

    Returns:
        A list of agent type information dictionaries
    """
    agent_types = []
    for agent_type, agent_class in cls._agent_registry.items():
      agent_types.append({
        "type": agent_type,
        "name": agent_type.lower(),
        "description": agent_class.get_description()
      })
    return agent_types

  @classmethod
  def process(cls, process: Process) -> Process:
    """
    Process the given process by dispatching to the appropriate agent implementation.

    Args:
        process: The process to be executed

    Returns:
        The updated process with results or error information
    """
    agent_class = cls.get_agent_for_type(process.agent_type)
    return agent_class.process(process)
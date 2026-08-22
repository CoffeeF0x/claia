"""
Base agent class for CLAIA.
Provides a common interface for all agent implementations.
"""

# External dependencies
import logging
from dataclasses import dataclass, field
from typing import Optional, Type

# Internal dependencies
from ...core.plugins.base import ExtensionInfo
from ..task import Task



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                          BASE AGENT CLASS                            #
########################################################################
class BaseAgent:
  """
  Base agent class that provides a common interface for all agents.

  Agents are responsible for processing requests using different strategies.
  Specific agent implementations should inherit from this class and implement
  the execute method.
  """

  @classmethod
  def run(cls, task: Task, registry, **kwargs) -> object:
    """
    Run a request and update the task with the result.

    Args:
        task: The task to execute
        registry: Registry instance to use for model operations
        **kwargs: Additional keyword arguments

    Returns:
        The updated task with results or error information
    """
    logger.info(f"Starting task {task.id} with agent {cls.__name__}")
    task.mark_started()

    try:
      # Validate common requirements before proceeding
      logger.debug(f"Validating requirements for task {task.id}")
      cls.validate_task(task, registry)

      # Run the request
      logger.debug(f"Calling execute for {task.id} with agent {cls.__name__}")
      result = cls.execute(task, registry=registry, **kwargs)

      logger.info(f"Successfully completed task {task.id}")
      return result
    except Exception as e:
      logger.exception(f"Error running {task.id} with agent {cls.__name__}: {str(e)}")
      task.mark_failed(str(e))
      return task

  @classmethod
  def execute(cls, task: Task, registry, **kwargs) -> object:
    """
    Implement the actual execution logic for this agent type.
    This method should be overridden by specific agent implementations.

    Args:
        task: The task to execute
        registry: Registry instance to use for model operations
        **kwargs: Additional keyword arguments

    Returns:
        The updated task with results
    """
    logger.error(f"execute not implemented for {cls.__name__}")
    raise NotImplementedError(f"Agent implementation {cls.__name__} must override execute")

  @classmethod
  def validate_task(cls, task: Task, registry) -> None:
    """
    Validate that the task has all the common requirements needed for execution.

    Args:
        task: The task to validate
        registry: Registry instance to use for validation

    Raises:
        ValueError: If any required component is missing
    """
    logger.debug(f"Validating task {task.id} requirements")

    # Check for conversation
    if not task.conversation:
      logger.error(f"Task {task.id} missing conversation")
      raise ValueError(f"{cls.__name__} requires a conversation to work with")

    # Check for model_id in parameters
    model_id = task.parameters.get("model_id")
    if not model_id:
      logger.error(f"Task {task.id} missing model_id in parameters")
      raise ValueError(f"{cls.__name__} requires a model_id in task parameters")

    # Check for model registry
    if not registry:
      logger.error(f"Task {task.id} has no registry available")
      raise ValueError(f"{cls.__name__} requires a registry to be provided")

    logger.debug(f"Task {task.id} validated successfully with model {model_id}")

  @classmethod
  def get_description(cls) -> str:
    """
    Get a description of this agent type.

    Returns:
        A string description of the agent
    """
    return cls.__doc__ or "No description available"


########################################################################
#                              AGENT INFO                              #
########################################################################
@dataclass
class AgentInfo(ExtensionInfo):
  """Information about an agent implementation.

  Extends ``ExtensionInfo`` with the concrete ``agent_class`` used for
  dispatch. Entry-point agents leave ``agent_class`` unset; the manager
  fills it from the loaded class at discovery. Programmatic
  ``Registry.register`` supplies it directly.
  """
  agent_class: Optional[Type[BaseAgent]] = field(default=None)

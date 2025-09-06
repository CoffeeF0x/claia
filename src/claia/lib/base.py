"""
Base agent class for CLAIA.
Provides a common interface for all agent implementations.
"""

# External dependencies
import logging

# Internal dependencies
from .process import Process



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
  the process_request method.
  """

  @classmethod
  def process(cls, process: Process, registry=None, **kwargs) -> object:
    """
    Process a request and update the process with the result.

    Args:
        process: The process to execute
        registry: Registry instance to use for model operations
        **kwargs: Additional keyword arguments

    Returns:
        The updated process with results or error information
    """
    logger.info(f"Starting process {process.id} with agent {cls.__name__}")
    process.mark_started()

    try:
      # Validate common requirements before proceeding
      logger.debug(f"Validating requirements for process {process.id}")
      cls.validate_process_requirements(process, registry)

      # Process the request
      logger.debug(f"Executing process_request for {process.id} with agent {cls.__name__}")
      result = cls.process_request(process, registry=registry, **kwargs)

      logger.info(f"Successfully completed process {process.id}")
      return result
    except Exception as e:
      logger.exception(f"Error processing {process.id} with agent {cls.__name__}: {str(e)}")
      process.mark_failed(str(e))
      return process

  @classmethod
  def process_request(cls, process: Process, registry=None, **kwargs) -> object:
    """
    Implement the actual processing logic for this agent type.
    This method should be overridden by specific agent implementations.

    Args:
        process: The process to execute
        registry: Registry instance to use for model operations
        **kwargs: Additional keyword arguments

    Returns:
        The updated process with results
    """
    logger.error(f"process_request not implemented for {cls.__name__}")
    raise NotImplementedError(f"Agent implementation {cls.__name__} must override process_request")

  @classmethod
  def validate_process_requirements(cls, process: Process, registry=None) -> None:
    """
    Validate that the process has all the common requirements needed for processing.

    Args:
        process: The process to validate
        registry: Registry instance to use for validation

    Raises:
        ValueError: If any required component is missing
    """
    logger.debug(f"Validating process {process.id} requirements")

    # Check for conversation
    if not process.conversation:
      logger.error(f"Process {process.id} missing conversation")
      raise ValueError(f"{cls.__name__} requires a conversation to work with")

    # Check for model_id in parameters
    model_id = process.parameters.get("model_id")
    if not model_id:
      logger.error(f"Process {process.id} missing model_id in parameters")
      raise ValueError(f"{cls.__name__} requires a model_id in process parameters")

    # Check for model registry
    if not registry:
      logger.error(f"Process {process.id} has no registry available")
      raise ValueError(f"{cls.__name__} requires a registry to be provided")

    logger.debug(f"Process {process.id} validated successfully with model {model_id}")

  @classmethod
  def get_description(cls) -> str:
    """
    Get a description of this agent type.

    Returns:
        A string description of the agent
    """
    return cls.__doc__ or "No description available"

"""
Base agent class for CLAIA.
Provides a common interface for all agent implementations.
"""

# External dependencies
import logging
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
  def process(cls, process: Process, **kwargs) -> object:
    """
    Process a request and update the process with the result.

    Args:
        process: The process to execute

    Returns:
        The updated process with results or error information
    """
    logger.info(f"Starting process {process.id} with agent {cls.__name__}")
    process.mark_started()

    try:
      # Validate common requirements before proceeding
      logger.debug(f"Validating requirements for process {process.id}")
      cls.validate_process_requirements(process)

      # Process the request
      logger.debug(f"Executing process_request for {process.id} with agent {cls.__name__}")
      result = cls.process_request(process, **kwargs)

      logger.info(f"Successfully completed process {process.id}")
      return result
    except Exception as e:
      logger.exception(f"Error processing {process.id} with agent {cls.__name__}: {str(e)}")
      process.mark_failed(str(e))
      return process

  @classmethod
  def process_request(cls, process: Process, **kwargs) -> object:
    """
    Implement the actual processing logic for this agent type.
    This method should be overridden by specific agent implementations.

    Args:
        process: The process to execute

    Returns:
        The updated process with results
    """
    logger.error(f"process_request not implemented for {cls.__name__}")
    raise NotImplementedError(f"Agent implementation {cls.__name__} must override process_request")

  @classmethod
  def validate_process_requirements(cls, process: Process) -> None:
    """
    Validate that the process has all the common requirements needed for processing.

    Args:
        process: The process to validate

    Raises:
        ValueError: If any required component is missing
    """
    logger.debug(f"Validating process {process.id} requirements")

    # Check for conversation
    if not process.conversation:
      logger.error(f"Process {process.id} missing conversation")
      raise ValueError(f"{cls.__name__} requires a conversation to work with")

    # Check for settings
    if not process.settings:
      logger.error(f"Process {process.id} missing settings")
      raise ValueError(f"{cls.__name__} requires settings to function")

    # Check for model_id (from parameters or settings)
    model_id = process.parameters.get("model_id", process.settings.active_model)
    if not model_id:
      logger.error(f"Process {process.id} missing model_id and no active model set")
      raise ValueError(f"{cls.__name__} requires an active model")

    # Add the validated model_id to process parameters for easy access
    process.parameters["model_id"] = model_id
    logger.debug(f"Process {process.id} validated successfully with model {model_id}")

  @classmethod
  def get_description(cls) -> str:
    """
    Get a description of this agent type.

    Returns:
        A string description of the agent
    """
    return cls.__doc__ or "No description available"

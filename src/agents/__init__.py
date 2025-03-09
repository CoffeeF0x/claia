"""
This module contains the agent system for CLAIA.
Agents process requests and manage the conversation flow.
"""

# External dependencies
import logging, uuid, time, queue, threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Type



##################################################
#                 INITIALIZATION                 #
##################################################
logger = logging.getLogger(__name__)



##################################################
#                     ENUMS                      #
##################################################
class ProcessStatus(Enum):
  """Status of a process."""
  PENDING = "pending"
  PROCESSING = "processing"
  COMPLETED = "completed"
  FAILED = "failed"
  CANCELLED = "cancelled"

class AgentType(Enum):
  """Types of agents that can handle processes."""
  SIMPLE = "simple"  # Simple agent that directly calls a model
  SIMPLE_TOOL = "simple-tool"  # Simple agent that can use tools

class SourcePreference(Enum):
  """Enum for source preferences when deploying models."""
  ANY = "any"  # Use any available source
  API = "api"  # Prefer API sources
  LOCAL = "local"  # Prefer local deployment
  REMOTE = "remote"  # Prefer remote deployment


##################################################
#                PROCESS CLASSES                 #
##################################################
class Process:
  """
  Represents a process to be executed by an agent.

  A process is a unit of work that can be executed by an agent.
  It contains all the information needed to execute the process,
  including the conversation context and any additional parameters.
  """
  def __init__(
    self,
    agent_type: AgentType = AgentType.SIMPLE,
    settings: Any = None,
    conversation: Any = None,
    parameters: Dict[str, Any] = None,
    parent_id: Optional[str] = None,
    id: Optional[str] = None
  ):
    """
    Initialize a new Process.

    Args:
        agent_type: The type of agent that should handle this process
        settings: The settings object to use for this process
        conversation: The conversation object to use for this process
        parameters: Additional parameters for this process
        parent_id: The ID of the parent process that created this process
        id: The ID of this process (generated if not provided)
    """
    self.id = id or str(uuid.uuid4())
    self.agent_type = agent_type
    self.status = ProcessStatus.PENDING
    self.parent_id = parent_id
    self.settings = settings
    self.conversation = conversation
    self.parameters = parameters or {}
    self.result = None
    self.error = None
    self.created_at = time.time()
    self.started_at = None
    self.completed_at = None

  def mark_started(self):
    """Mark the process as started."""
    self.status = ProcessStatus.PROCESSING
    self.started_at = time.time()

  def mark_completed(self, result: Any = None):
    """Mark the process as completed with an optional result."""
    self.status = ProcessStatus.COMPLETED
    self.result = result
    self.completed_at = time.time()

  def mark_failed(self, error: str):
    """Mark the process as failed with an error message."""
    self.status = ProcessStatus.FAILED
    self.error = error
    self.completed_at = time.time()

  def mark_cancelled(self):
    """Mark the process as cancelled."""
    self.status = ProcessStatus.CANCELLED
    self.completed_at = time.time()

class ProcessQueue:
  """
  A thread-safe queue for processes.

  This queue is used to manage processes that need to be executed by agents.
  Processes are processed in FIFO (First In, First Out) order.
  """
  def __init__(self):
    """Initialize a new ProcessQueue."""
    self._queue = queue.Queue()
    self._lock = threading.Lock()
    self._processes = {}  # id -> Process mapping for quick lookups

  def put(self, process: Process):
    """
    Add a process to the queue.

    Args:
        process: The process to add to the queue

    Returns:
        The ID of the process
    """
    with self._lock:
      # Store in our lookup dictionary
      self._processes[process.id] = process

      # Add to queue
      self._queue.put(process.id)

    return process.id

  def get(self, block=True, timeout=None) -> Optional[Process]:
    """
    Get the next process from the queue.

    Args:
        block: Whether to block until a process is available
        timeout: How long to wait for a process to become available

    Returns:
        The next process from the queue, or None if no process is available
    """
    try:
      process_id = self._queue.get(block=block, timeout=timeout)
      with self._lock:
        process = self._processes.get(process_id)
        if process:
          # Only remove from processes dict if status is COMPLETED, FAILED, or CANCELLED
          if process.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.CANCELLED]:
            self._processes.pop(process_id, None)
          return process
        return None
    except queue.Empty:
      return None

  def get_by_id(self, process_id: str) -> Optional[Process]:
    """
    Get a process by its ID without removing it from the queue.

    Args:
        process_id: The ID of the process to get

    Returns:
        The process with the given ID, or None if no such process exists
    """
    with self._lock:
      return self._processes.get(process_id)

  def update(self, process: Process):
    """
    Update a process in the queue.

    Args:
        process: The process to update
    """
    with self._lock:
      self._processes[process.id] = process

  def remove(self, process_id: str) -> bool:
    """
    Remove a process from the queue.

    Note: This doesn't remove from the queue directly
    (which is not easily possible), but marks it as cancelled
    so it will be ignored when retrieved.

    Args:
        process_id: The ID of the process to remove

    Returns:
        True if the process was found and cancelled, False otherwise
    """
    with self._lock:
      process = self._processes.get(process_id)
      if process:
        process.mark_cancelled()
        return True
      return False

  def size(self) -> int:
    """
    Get the number of processes in the queue.

    Returns:
        The number of processes in the queue
    """
    with self._lock:
      return len(self._processes)



##################################################
#                 AGENTS CLASSES                 #
##################################################
class Agent:
  """
  Agent class that processes requests.

  This class provides a static method to process a request based on its agent type.
  """
  @staticmethod
  def process(process: Process) -> Process:
    """
    Process the given process and return the updated process.

    This method will create the appropriate agent based on the process's agent_type
    and use it to process the request.

    Args:
        process: The process to be executed

    Returns:
        The updated process with results or error information
    """
    process.mark_started()

    try:
      # Determine which agent type to use
      if process.agent_type == AgentType.SIMPLE:
        return SimpleAgent.process(process)
      elif process.agent_type == AgentType.SIMPLE_TOOL:
        # TODO: Implement SimpleToolAgent
        raise NotImplementedError(f"Agent type {process.agent_type} not implemented")
      else:
        raise ValueError(f"Unknown agent type: {process.agent_type}")
    except Exception as e:
      logger.exception(f"Error processing {process.id}: {str(e)}")
      process.mark_failed(str(e))
      return process

class SimpleAgent:
  """
  A simple agent that directly calls a model for inference.

  This agent is the most basic implementation that maintains existing
  program functionality by directly calling a specified model.
  """
  @staticmethod
  def process(process: Process) -> Process:
    """
    Process a model inference request.

    Args:
        process: The process to execute

    Returns:
        The updated process with results or error information
    """
    try:
      # Get the conversation and settings from the process
      conversation = process.conversation
      settings = process.settings
      source_preference = process.parameters.get("source_preference", SourcePreference.ANY)

      if not conversation:
        raise ValueError("Conversation is required for SimpleAgent")

      if not settings:
        raise ValueError("Settings are required for SimpleAgent")

      # Get the active model from settings
      model_id = settings.active_model
      if not model_id:
        raise ValueError("No active model set in settings")

      # Import here to avoid circular imports
      from models import run as model_run

      # Run the model with the conversation
      result = model_run(model_id, conversation.get_formatted_messages(), settings=settings)

      if hasattr(result, 'is_error') and result.is_error():
        raise ValueError(f"Error running model: {result.get_message()}")

      response = result.data if hasattr(result, 'data') else result

      # Process the response
      logger.info(f"SimpleAgent processed request with model {model_id}")
      process.mark_completed({
        "response": response,
        "model": model_id,
        "source": "actual"
      })
    except Exception as e:
      logger.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process


##################################################
#                      MAIN                      #
##################################################
# Example usage
if __name__ == "__main__":
  # Set up logging
  logging.basicConfig(level=logging.INFO)

  # Create a process queue
  process_queue = ProcessQueue()

  # Import the Conversation class
  from conversations import Conversation, MessageRole

  # Create a conversation
  conversation = Conversation(
    conversation_directory="conversations",
    artifacts_directory="artifacts",
    title="Test Conversation",
    files_subdirectory="files"
  )
  conversation.add_message(MessageRole.USER, "Hello, how are you?")

  # Mock settings
  class MockSettings:
    active_model = "gpt-4"
    conversation_directory = "conversations"
    artifacts_directory = "artifacts"
    conversation_files_directory = "files"

  settings = MockSettings()

  # Create a process
  process = Process(
    agent_type=AgentType.SIMPLE,
    settings=settings,
    conversation=conversation,
    parameters={
      "source_preference": SourcePreference.ANY
    }
  )

  # Add the process to the queue
  process_id = process_queue.put(process)

  # Get the process from the queue
  process = process_queue.get()

  # Process the request
  result_process = Agent.process(process)

  # Update the process in the queue
  process_queue.update(result_process)

  # Check the process status
  print(f"Process status: {result_process.status}")
  print(f"Process result: {result_process.result}")

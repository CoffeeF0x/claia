"""
This module contains the agent system for CLAIA.
Agents process requests and manage the conversation flow.
"""

# External dependencies
import logging, uuid, time, queue, threading
from typing import Optional, Dict, List, Any, Type

# Internal dependencies
from models import run as model_run, ModelCapability, definitions
from errors import Result
from enums import ProcessStatus, AgentType, SourcePreference, MessageRole
from files import Conversation
from settings import Settings
from .simple import SimpleAgent
from .bob import BobAgent



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                           PROCESS CLASSES                            #
########################################################################
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
    settings: Settings = None,
    conversation: Conversation = None,
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

  def process(self, block=False, timeout=None) -> Optional[Process]:
    """
    Get a process from the queue and process it using the Agent class.

    Args:
        block: Whether to block until a process is available
        timeout: How long to wait for a process to become available

    Returns:
        The processed Process object or None if no process was available
    """
    # Get the next process from the queue
    process = self.get(block=block, timeout=timeout)
    if not process or process.status != ProcessStatus.PENDING:
      return None

    # Process the request directly with the Agent class
    updated_process = Agent.process(process)

    # Update the process in the queue
    self.update(updated_process)

    return updated_process

  def process_by_id(self, process_id: str) -> Optional[Process]:
    """
    Process a specific process identified by its ID.

    Args:
        process_id: The ID of the process to process

    Returns:
        The processed Process object or None if the process wasn't found
        or wasn't in a PENDING state
    """
    with self._lock:
      process = self._processes.get(process_id)
      if not process or process.status != ProcessStatus.PENDING:
        return None

    # Process the request directly with the Agent class
    updated_process = Agent.process(process)

    # Update the process in the queue
    self.update(updated_process)

    return updated_process



########################################################################
#                       CONVERSATION PROCESSING                        #
########################################################################
def process_conversation_for_capability(capability: ModelCapability, conversation, parameters=None):
  """
  Process a conversation based on the specified model capability.

  Args:
      capability: The model capability to process for
      conversation: The conversation object to process
      parameters: Additional parameters for processing

  Returns:
      A list of formatted messages ready to be passed to model_run
  """
  if not conversation:
    raise ValueError("Conversation is required for processing")

  parameters = parameters or {}

  # Get formatted messages from the conversation
  messages = conversation.get_formatted_messages()

  # Process based on capability
  if capability == ModelCapability.TTT:
    # Text-to-text processing - return messages as is
    return messages

  elif capability == ModelCapability.TTI:
    # Text-to-image processing
    # Extract prompt from last user message
    prompt = None
    for message in reversed(messages):
      if message.get('role') == 'user':
        prompt = message.get('content', '')
        break

    if not prompt:
      raise ValueError("Text-to-image requires a text prompt")

    # Apply any generation parameters from the request
    generation_params = parameters.get("generation_params", {})

    # Return prompt message for TTI processing
    return [{"role": "user", "content": prompt, "generation_params": generation_params}]

  elif capability == ModelCapability.ITT:
    # Image-to-text processing
    image_data = None
    prompt = None

    # Extract prompt and image from the last user message
    for message in reversed(messages):
      if message.get('role') == 'user':
        prompt = message.get('content', '')
        # Look for image data in the message
        if 'images' in message:
          image_data = message.get('images', [])[0]
        break

    if not image_data:
      raise ValueError("Image-to-text requires image data")

    # Return message with image for ITT processing
    return [{"role": "user", "content": prompt, "image": image_data}]

  elif capability == ModelCapability.TTA:
    # Text-to-audio processing
    text = None
    for message in reversed(messages):
      if message.get('role') == 'user':
        text = message.get('content', '')
        break

    if not text or not isinstance(text, str):
      raise ValueError("Text-to-audio requires non-empty text")

    # Return text message for audio generation
    return [{"role": "user", "content": text}]

  elif capability == ModelCapability.TAI:
    # Text and image capability
    # Return messages as is, they should already contain text and images
    return messages

  else:
    # Default processing - return formatted messages
    return messages



########################################################################
#                           AGENT REGISTRY                             #
########################################################################
# Registry to store agent implementations
AGENT_REGISTRY = {}

def register_agent(agent_type: AgentType, agent_class: Type):
  """
  Register an agent implementation for a specific agent type.

  Args:
      agent_type: The type of agent to register
      agent_class: The agent class implementation
  """
  AGENT_REGISTRY[agent_type] = agent_class
  logger.debug(f"Registered agent {agent_class.__name__} for type {agent_type.value}")

def get_agent_for_type(agent_type: AgentType):
  """
  Get the agent implementation for a specific agent type.

  Args:
      agent_type: The type of agent to get

  Returns:
      The agent class for the specified type, or SimpleAgent if not found
  """
  agent_class = AGENT_REGISTRY.get(agent_type)
  if not agent_class:
    logger.warning(f"No agent registered for type {agent_type.value}, using SimpleAgent")
    return SimpleAgent
  return agent_class



########################################################################
#                            AGENT CLASS                               #
########################################################################
class Agent:
  """
  Agent class that serves as the entry point for processing requests.

  This class dispatches process requests to the appropriate agent implementation
  based on the process's agent_type.
  """

  @staticmethod
  def get_agent_types() -> List[Dict[str, Any]]:
    """
    Get a list of all available agent types with descriptions.

    Returns:
        A list of agent type information dictionaries
    """
    agent_types = []
    for agent_type in AgentType:
      agent_class = get_agent_for_type(agent_type)
      agent_types.append({
        "type": agent_type.value,
        "name": agent_type.name,
        "description": agent_class.get_description(),
        "capabilities": agent_class.get_capabilities()
      })
    return agent_types

  @staticmethod
  def process(process: Process) -> Process:
    """
    Process the given process by dispatching to the appropriate agent implementation.

    Args:
        process: The process to be executed

    Returns:
        The updated process with results or error information
    """
    agent_class = get_agent_for_type(process.agent_type)
    return agent_class.process(process)



########################################################################
#                        REGISTER DEFAULT AGENTS                       #
########################################################################
# Register the default agent implementations
register_agent(AgentType.SIMPLE, SimpleAgent)
register_agent(AgentType.BOB, BobAgent)



########################################################################
#                                 MAIN                                 #
########################################################################
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
    base_directory="conversations",
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

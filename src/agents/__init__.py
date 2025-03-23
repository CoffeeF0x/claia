"""
This module contains the agent system for CLAIA.
Agents process requests and manage the conversation flow.
"""

# External dependencies
import logging, uuid, time, queue, threading, os
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable, Type

# Internal dependencies
from models import run as model_run, ModelCapability
from models.definitions import definitions
from errors import Result
from enums import ProcessStatus, AgentType, SourcePreference, MessageRole



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              CONSTANTS                               #
########################################################################
# Bob Agent's system prompt
BOB_SYSTEM_PROMPT = """
You are Bob, a straightforward and no-nonsense assistant.
Bob speaks in the third person and keeps responses brief.
Bob doesn't use flowery language.
Bob is direct and sometimes sarcastic.
Bob always tries to be helpful despite his gruff demeanor.
"""



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
  def process(cls, process: Process) -> Process:
    """
    Process a request and update the process with the result.

    Args:
        process: The process to execute

    Returns:
        The updated process with results or error information
    """
    process.mark_started()

    try:
      return cls.process_request(process)
    except Exception as e:
      logger.exception(f"Error processing {process.id}: {str(e)}")
      process.mark_failed(str(e))
      return process

  @classmethod
  def process_request(cls, process: Process) -> Process:
    """
    Implement the actual processing logic for this agent type.
    This method should be overridden by specific agent implementations.

    Args:
        process: The process to execute

    Returns:
        The updated process with results
    """
    raise NotImplementedError("Agent implementations must override process_request")

  @classmethod
  def get_description(cls) -> str:
    """
    Get a description of this agent type.

    Returns:
        A string description of the agent
    """
    return cls.__doc__ or "No description available"

  @classmethod
  def get_capabilities(cls) -> List[str]:
    """
    Get a list of this agent's capabilities.

    Returns:
        A list of capability strings
    """
    return ["process"]



########################################################################
#                           AGENT CLASSES                              #
########################################################################
class SimpleAgent(BaseAgent):
  """
  A simple agent that directly calls a model for inference.

  This agent serves as the central gateway for all direct model interactions,
  translating between agent requests and model capabilities.
  """

  @classmethod
  def process_request(cls, process: Process) -> Process:
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

      if not conversation:
        raise ValueError("Conversation is required for SimpleAgent")

      if not settings:
        raise ValueError("Settings are required for SimpleAgent")

      # Get the model ID from settings or process parameters
      model_id = process.parameters.get("model_id", settings.active_model)
      if not model_id:
        raise ValueError("No active model set in settings")

      # Determine the capability based on the process parameters or model definition
      capability = process.parameters.get("capability")

      # If capability not specified, get it from the model definition
      if not capability and model_id in definitions:
        model_def = definitions[model_id]
        if "capabilities" in model_def and model_def["capabilities"]:
          capability = model_def["capabilities"][0]  # Use the first capability
          logger.debug(f"Using capability {capability} from model definition")

      # Default to text-to-text if still not determined
      if not capability:
        capability = ModelCapability.TTT
        logger.debug("No capability specified, defaulting to text-to-text")

      # Process the conversation based on the capability
      processed_messages = process_conversation_for_capability(
        capability,
        conversation,
        process.parameters
      )

      # Run the model with the processed messages
      result = model_run(model_id, processed_messages, settings=settings, process_type=capability)

      if result.is_error():
        raise ValueError(f"Error running model: {result.get_message()}")

      # Handle the result based on capability
      if capability == ModelCapability.TTI:
        # Handle image result
        image = result.data

        # Save the generated image
        image_path = os.path.join(settings.artifacts_directory, f"{uuid.uuid4()}.png")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path)

        # Add the image to the conversation
        file_id = conversation.add_file(image_path)

        # Add assistant message with the image
        if file_id:
          conversation.add_message(
            MessageRole.ASSISTANT,
            "Here's the generated image:",
            file_paths=[image_path]
          )

          process.mark_completed({
            "response": "Image generated successfully",
            "model": model_id,
            "source": "text-to-image",
            "image_path": image_path,
            "file_id": file_id
          })
        else:
          raise ValueError("Failed to add image to conversation")
      elif capability == ModelCapability.TTA:
        # Handle audio result (placeholder for now)
        process.mark_completed({
          "response": "Audio generation not yet fully implemented",
          "model": model_id,
          "source": "text-to-audio"
        })
      else:
        # Default text response handling
        process.mark_completed({
          "response": result.data,
          "model": model_id,
          "source": capability.value
        })

    except Exception as e:
      logger.exception(f"Error in SimpleAgent for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process

  @classmethod
  def get_capabilities(cls) -> List[str]:
    """
    Get a list of SimpleAgent's capabilities.

    Returns:
        A list of capability strings
    """
    return ["text", "image", "audio"]

class BobAgent(BaseAgent):
  """
  Bob is a gruff, straightforward, no-nonsense assistant with a unique personality.

  Bob only works with text-to-text models and has his own system prompt.
  """

  @classmethod
  def process_request(cls, process: Process) -> Process:
    """
    Process a request using Bob's unique style.

    Args:
        process: The process to execute

    Returns:
        The updated process with results
    """
    try:
      # Get the conversation and settings from the process
      conversation = process.conversation
      settings = process.settings

      if not conversation:
        raise ValueError("Bob needs a conversation to work with")

      if not settings:
        raise ValueError("Bob needs settings to function")

      # Get the model ID from settings or process parameters
      model_id = process.parameters.get("model_id", settings.active_model)
      if not model_id:
        raise ValueError("Bob needs a model to use")

      # Check if the model has text-to-text capability
      if model_id in definitions:
        model_def = definitions[model_id]
        capabilities = model_def.get("capabilities", [])

        if ModelCapability.TTT not in capabilities:
          raise ValueError("Bob only works with text-to-text models")
      else:
        raise ValueError(f"Bob doesn't recognize the model: {model_id}")

      # Set or update the system prompt to Bob's prompt
      original_system_prompt = None
      if conversation.system_prompt:
        # Save the original system prompt to restore later
        original_system_prompt = conversation.system_prompt

      # Set Bob's system prompt
      conversation.update_system_prompt(BOB_SYSTEM_PROMPT)

      try:
        # Process the conversation for text-to-text capability
        processed_messages = process_conversation_for_capability(
          ModelCapability.TTT,
          conversation,
          process.parameters
        )

        # Run the model with the processed messages
        result = model_run(model_id, processed_messages, settings=settings, process_type=ModelCapability.TTT)

        if result.is_error():
          raise ValueError(f"Bob ran into a problem: {result.get_message()}")

        # Complete the process with the result
        process.mark_completed({
          "response": result.data,
          "model": model_id,
          "source": "bob"
        })

      finally:
        # Restore the original system prompt if there was one
        if original_system_prompt:
          conversation.update_system_prompt(original_system_prompt)

    except Exception as e:
      logger.exception(f"Bob encountered an error for {process.id}: {str(e)}")
      process.mark_failed(str(e))

    return process

  @classmethod
  def get_capabilities(cls) -> List[str]:
    """
    Get a list of Bob's capabilities.

    Returns:
        A list of capability strings
    """
    return ["text"]



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

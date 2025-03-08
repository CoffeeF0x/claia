# TODO:
# - create new characters or update existing (need to move characters to json files)
# - add streaming support
# - models should be chosen by the user via key, and passed to the ai via another key pair in its definition
# - add ability to rename conversations, and perhaps have ai name conversations automatically
# - create an option to enable a server that serves and updates md files, and sync conversations to md files
# - Needs a way to filter models (since there are lots) (model list partname?)
# - function calling doesn't work on most functions (the function calling name is just the final leaf rather than a distinct function name, which is leading to collisions)
# - run single commands from cli, for example: claia transcribe --file <audio-file>
# - if a command has an alias, or perhaps just if it's alias matches the root of that path the rest of the commands aren't displayed (in help or executable, test by adding list alias to mc list instances)

# External dependencies
import readline
import atexit
import time
import logging
import queue
import os

# Internal dependencies
from commands import get_function_definitions, run as command
from errors import Result
from settings import Settings
from utilities import *
from tools import process_function_calls
from agents import ProcessQueue, Process, Agent, AgentType, SourcePreference, ProcessStatus
from conversations import Conversation, MessageRole



###########################################################################
#                               CONSTANTS                                 #
###########################################################################
HISTORY_FILE = ".claia_history"
MAX_HISTORY_LEN = 1000



###########################################################################
#                             INITIALIZATION                              #
###########################################################################
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



###########################################################################
#                           UTILITY FUNCTIONS                             #
###########################################################################
def setup_command_history() -> None:
  """Initialize readline for command history with arrow key navigation."""
  try:
    # Ensure the history file directory exists only if needed
    history_dir = os.path.dirname(HISTORY_FILE)
    if history_dir and not os.path.exists(history_dir):
      os.makedirs(history_dir, exist_ok=True)

    # Try to read the history file
    readline.read_history_file(HISTORY_FILE)
    readline.set_history_length(MAX_HISTORY_LEN)
  except FileNotFoundError:
    pass
  except Exception as e:
    logger.error(f"Error setting up command history: {e}")

  atexit.register(readline.write_history_file, HISTORY_FILE)

def get_user_input() -> str:
  """Get and return user input using a standardized prompt symbol."""
  return input(":")



###########################################################################
#                         CONVERSATION FUNCTIONS                          #
###########################################################################
def create_conversation(settings: Settings, user_input: str = None) -> Conversation:
  """
  Create a conversation object from settings and user input.

  Args:
      settings: The application settings
      user_input: Optional user input to add to the conversation

  Returns:
      A conversation object
  """
  # If we have an active conversation in settings, use it
  if settings.active_conversation:
    conversation = settings.active_conversation
    if settings.active_prompt:
      conversation.update_system_prompt_if_empty(settings.active_prompt.get_formatted_prompt())

  # Otherwise, create a new conversation
  else:
    system_prompt = settings.active_prompt.get_formatted_prompt() if settings.active_prompt else None

    conversation = Conversation(
      conversation_directory=settings.conversation_directory,
      artifacts_directory=settings.artifacts_directory,
      title="New Conversation",
      system_prompt=system_prompt,
      files_subdirectory=settings.conversation_files_directory
    )
    settings.active_conversation = conversation

  # Add the user's message if not empty
  if user_input:
    conversation.add_message(MessageRole.USER, user_input)

  return conversation

def save_conversation_response(conversation: Conversation, response: str, settings: Settings) -> str:
  """
  Process the response, save it to the conversation, and return the final response.

  Args:
      conversation: The conversation object
      response: The raw response from the agent
      settings: The application settings

  Returns:
      The final processed response
  """
  # Process any function calls in the response
  processed_response = process_function_calls(response, settings)

  # Check if function calls were processed by comparing responses
  if processed_response != response:
    # Add the processed response to the conversation
    conversation.add_message(MessageRole.TOOL, processed_response)
    final_response = processed_response
  else:
    final_response = response

  # Add the assistant's response to the conversation
  conversation.add_message(MessageRole.ASSISTANT, final_response)
  conversation.save()

  return final_response



###########################################################################
#                            AGENT FUNCTIONS                              #
###########################################################################
def process_next_in_queue(settings: Settings, process_queue: ProcessQueue) -> None:
  """
  Process the next pending item in the queue.

  Args:
      settings: The application settings
      process_queue: The process queue
  """
  try:
    # Get the next process from the queue
    process = process_queue.get(block=False)
    if not process or process.status != ProcessStatus.PENDING:
      return

    # Process the request directly with the Agent class
    updated_process = Agent.process(process)

    # Update the process in the queue
    process_queue.update(updated_process)

    # Handle the completed process
    if updated_process.status == ProcessStatus.COMPLETED:
      # Get the conversation from the process
      conversation = updated_process.conversation

      # Get the response from the process result
      result = updated_process.result
      response = result.get("response", "No response from agent")

      # Save the response to the conversation and get the final response
      final_response = save_conversation_response(conversation, response, settings)

      # Display the response
      print(final_response)

    elif updated_process.status == ProcessStatus.FAILED:
      print(f"Error: {updated_process.error}")

  except queue.Empty:
    pass
  except Exception as e:
    logger.exception(f"Error processing request: {str(e)}")
    print(f"Error: {str(e)}")

def process_user_input(user_input: str, settings: Settings, process_queue: ProcessQueue) -> Result:
  """
  Process user input, either as a command or as a query to the LLM.

  Args:
      user_input: The user's input
      settings: The application settings
      process_queue: The process queue

  Returns:
      A Result object indicating success or failure
  """
  result = Result()

  if user_input and user_input[0] == ":":
    # Process as a command
    result = command(user_input[1:], settings)
  else:
    # Process as a query to the LLM
    # Create a conversation with the user's input
    conversation = create_conversation(settings, user_input)

    # Create a process with all necessary information
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

    # Process the queue until this process is completed
    while True:
      process_next_in_queue(settings, process_queue)

      # Check if the process is completed
      updated_process = process_queue.get_by_id(process.id)
      if not updated_process:
        print("Error: Process not found")
        break

      if updated_process.status in [ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.CANCELLED]:
        break

      # Sleep a bit to avoid busy waiting
      time.sleep(0.1)

  return result



###########################################################################
#                           FUNCTION DEFINITIONS                          #
###########################################################################
def load_function_definitions(settings: Settings) -> None:
  """
  Load function definitions into the settings object.

  Args:
      settings: The application settings
  """
  try:
    # Get function definitions from commands
    function_definitions = get_function_definitions(settings)

    # Set function definitions in settings
    settings.set_function_definitions(function_definitions)

    # Debug output
    print(f"Loaded {len(function_definitions)} function definitions")
  except Exception as e:
    logger.error(f"Error loading function definitions: {e}")
    # Initialize with empty list in case of error
    settings.set_function_definitions([])



###########################################################################
#                              MAIN FUNCTION                              #
###########################################################################
def main() -> None:
  """Main application entry point."""
  # Create application settings
  settings = Settings()

  # Initialize the process queue
  process_queue = ProcessQueue()

  # Set up command history with arrow key navigation
  setup_command_history()

  # Load function definitions into settings
  load_function_definitions(settings)

  # Main application loop
  result = Result()
  while not result.is_exit():
    # Process any pending items in the queue
    process_next_in_queue(settings, process_queue)

    # Get user input
    user_input = get_user_input()

    # Only add non-empty inputs to history
    if user_input.strip():
      readline.add_history(user_input)

    if settings.active_prompt:
      settings.apply_function_definitions_to_active_prompt()

    # Process the user input
    result = process_user_input(user_input, settings, process_queue)

    # Display any error messages
    if result.is_error():
      print(result.get_message())

  # Display exit message
  print(result.get_message())

# Call main function
if __name__ == "__main__":
  main()

# TODO:
# - create an option to enable a server that serves and updates md files, and sync conversations to md files?
# - Needs a way to filter models (since there are lots) (model list partname?)
# - perhaps have the model layer compare the capabilities against the sent request, if there's content that the model doesn't support throw a warning, maybe also trim the request to the model's capabilities
# - model should pass model name from source list in definitions rather than using the model id
# - Top level commands no longer show in command help

# - add ability to rename conversations, and perhaps have ai name conversations automatically

# - add streaming support
# - make process queue run in its own thread (so we can have async message processing)

# - create new prompts or update existing (need to move prompts to json files)
# - update system command to allow settings updates (and save to .env file?)
# - prompt doesn't apply to the active conversation (if there's an active conversation, it should apply to it)

# - add a function to check model capabilities in the registry, that will also consider model names that aren't in the definitions table (see bob as the primary use case)
# - add module imports for agents and migrate bob to be a module
# - create a vix demo that uses a list off images to show reactions in a conversation, think emojis (this should be a tool call since it's not generating the images, thought it's an idea to train a lora and have images generated)

# - each command should have a small object to define flags, this will allow us to seperate global flags from command flags?
# - prep all commands and models for kwargs (for specific settings, they can be passed via the settings extra args)
# - update commands to support kwargs so we can pass parameters without message="asdf" for example and just pass something like "asdf" directly (this works with positional args)
# - run commands from cli with optional --flags processing instead of arg=value style, for example: claia transcribe --file <audio-file>

# External dependencies
import readline
import atexit
import time
import logging
import os
import sys

# Internal dependencies
from commands import CommandRegistry
from results import Result
from settings import Settings
from agents import ProcessQueue, Process
from enums import SourcePreference, ProcessStatus, MessageRole
from files import Conversation
from defaults import initialize_defaults
from logger import initialize_logging
from mod import initialize_module_system



########################################################################
#                              CONSTANTS                               #
########################################################################
HISTORY_FILE = ".claia_history"
MAX_HISTORY_LEN = 1000
COMMAND_CHARACTER = ":"
INPUT_CHARACTER = ":"
DEFAULT_AGENT = "simple"



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def setup_command_history() -> None:
  """Initialize readline for command history with arrow key navigation."""
  logger.debug("Setting up command history")
  try:
    # Ensure the history file directory exists only if needed
    history_dir = os.path.dirname(HISTORY_FILE)
    if history_dir and not os.path.exists(history_dir):
      logger.debug(f"Creating history directory: {history_dir}")
      os.makedirs(history_dir, exist_ok=True)

    # Try to read the history file
    logger.debug(f"Reading history from file: {HISTORY_FILE}")
    readline.read_history_file(HISTORY_FILE)
    readline.set_history_length(MAX_HISTORY_LEN)
    logger.debug(f"Command history initialized with max length: {MAX_HISTORY_LEN}")
  except FileNotFoundError:
    logger.debug(f"History file not found, will create on exit: {HISTORY_FILE}")
  except Exception as e:
    logger.error(f"Error setting up command history: {e}")

  atexit.register(readline.write_history_file, HISTORY_FILE)
  logger.debug("Registered history file write on exit")


def get_user_input() -> str:
  """Get and return user input using a standardized prompt symbol."""
  logger.debug("Waiting for user input")
  return input(INPUT_CHARACTER)



########################################################################
#                                 MAIN                                 #
########################################################################
def main() -> None:
  """Main application entry point."""
  try:
    # Initialize the application
    logger.info("Initializing CLAIA...")
    settings = Settings()
    settings.root_logger = initialize_logging(settings.log_level, settings.log_format)
    settings = initialize_defaults(settings)

    # Log application startup with version and environment info
    logger.info("CLAIA application starting")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Platform: {sys.platform}")
    logger.debug(f"Current directory: {os.getcwd()}")
    logger.debug(f"Log level: {settings.log_level}")
    logger.debug(f"Log format: {settings.log_format}")
    if settings.log_file:
      logger.debug(f"Log file: {settings.log_file}")
    for arg in settings.extra_args:
      logger.debug(f"Stored extra argument: {arg}")

    # Initialize the command registry
    logger.debug("Initializing command registry")
    command_registry = CommandRegistry()

    # Initialize the module system (must happen after commands are initialized)
    logger.debug("Initializing module system")
    initialize_module_system(command_registry, settings.modules_directory)

    # Initialize the process queue
    logger.debug("Initializing process queue")
    process_queue = ProcessQueue()

    # Set up command history with arrow key navigation
    setup_command_history()

    # Log active model, agent, and prompt information
    logger.debug(f"Active model: {settings.active_model}")
    logger.debug(f"Active agent: {settings.active_agent}")
    logger.debug(f"Active prompt: {settings.active_prompt.prompt_name if settings.active_prompt else 'None'}")

    # Check for and process command line arguments
    if settings.extra_args:
      # Process command line arguments using the registry
      logger.info(f"Processing command line arguments: {' '.join(settings.extra_args)}")
      result = command_registry.run(settings.extra_args, settings)

      # Display the result
      if result.get_message():
        print(result.get_message())

      # Exit after running the command
      logger.info("CLAIA exiting after CLI command execution")
      return

    logger.info("CLAIA initialization complete, entering main loop")

    # Main application loop
    result = Result()
    while not result.is_exit():
      # Initialize and clear variables
      process = None
      response = None
      last_response = None

      # Wait for user input
      user_input = get_user_input()

      # Populate command history if input is not empty
      if user_input.strip():
        logger.debug("Adding user input to history")
        readline.add_history(user_input)

      # Process user input as either a command or a query
      if user_input and user_input[0] == COMMAND_CHARACTER:
        logger.debug(f"Processing as command: {user_input[1:]}")
        result = command_registry.run(user_input[1:].split(), settings)
        print(result.message)
      else:
        # Create a new conversation if one doesn't exist
        if not settings.active_conversation:
          settings.active_conversation = Conversation(
            settings.files_directory,
            registry=command_registry
          )

        # Set the active agent if one doesn't exist
        if not settings.active_agent:
          settings.active_agent = DEFAULT_AGENT

        settings.active_conversation.add_message(MessageRole.USER, user_input)

        process = Process(
          agent_type=settings.active_agent,
          settings=settings,
          conversation=settings.active_conversation,
          parameters={
            "source_preference": SourcePreference.ANY,
            "model_id": settings.active_model
          }
        )

        process_id = process_queue.put(process)
        logger.debug(f"Process added with ID: {process_id}")

        # Loop through the queue until the process is completed
        logger.debug(f"Waiting for process to complete: {process.id}")
        while process.status == ProcessStatus.PENDING or process.status == ProcessStatus.PROCESSING:
          process = process_queue.process_by_id(process.id)

          if process.status == ProcessStatus.PROCESSING:
            response = process.conversation.get_latest_message()

            if last_response and response and len(response.content) > len(last_response.content):
              new_content = response.content[len(last_response.content):]
              print(new_content, end='', flush=True)

            last_response = response

          # Sleep a bit to avoid busy waiting
          time.sleep(0.1)

        logger.debug(f"Process completed: {process.id}")

        # If the process is completed, display the rest of the response
        if process.status == ProcessStatus.COMPLETED:
          if response:
            print(process.conversation.get_latest_message().content[len(response.content):])
          else:
            print(process.conversation.get_latest_message().content)
          process.conversation.save()
        elif process.status == ProcessStatus.FAILED:
          logger.error(f"Process failed: {process.error}")
        elif process.status == ProcessStatus.CANCELLED:
          logger.warning(f"Process cancelled: {process.error}")

      # Display any error messages
      if result.is_error():
        logger.debug(f"Error result: {result.get_message()}")
        print(f"Error: {result.get_message()}")

    # Display exit message
    logger.info(f"CLAIA application exiting: {result.get_message()}")

  except Exception as e:
    logger.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
    sys.exit(1)



if __name__ == "__main__":
  main()

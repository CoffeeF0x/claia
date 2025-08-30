# TODO:
# - create an option to enable a server that serves and updates md files, and sync conversations to md files?
# - Needs a way to filter models (since there are lots) (model list partname?)
# - perhaps have the model layer compare the capabilities against the sent request, if there's content that the model doesn't support throw a warning, maybe also trim the request to the model's capabilities
# - create a new image agent that exports the images after generation
# - create a vix demo that uses a list off images to show reactions in a conversation, think emojis (this should be a tool call since it's not generating the images, thought it's an idea to train a lora and have images generated)

# - Top level commands no longer show in command help
# - run commands from cli with optional --flags processing instead of arg=value style, for example: claia transcribe --file <audio-file>
# - create new prompts or update existing (need to move prompts to json files)
# - update system command to allow settings updates (and save to .env file?)
# - prompt doesn't apply to the active conversation (if there's an active conversation, it should apply to it)

# - add ability to rename conversations, and perhaps have ai name conversations automatically
# - Need to clean input from user and models (set gpt-4 to temperature 2 causing issues)
# - Add multi-gpu support for transformer models
# - local models aren't using model path

# - local models should check ram and download size and confirm resource availability?
# - local models should have flags to select cpu or gpu, or specify certain gpus or memory usage
# - local models may suggest a quantized version of the model that may fit
# - (Consider the posibility of a hybrid deployment, where model is loaded into cpu memory, but moved to gpu memory when processing requests to allow several models to run on a single machine)
# - (or perhaps there's a deployment manager, and the deployment object contains methods to move the model between cpu and gpu as needed)



# External dependencies
import readline
import atexit
import time
import logging
import os
import sys
from typing import Optional, Dict, Any

# Internal dependencies
# from claia.commands import CommandRegistry
from claia.agents import Process, AgentRegistry
from claia.common.results import Result
from claia.common.enums.agent import ProcessStatus, SourcePreference
from claia.common.enums.conversation import MessageRole
from claia.common.files.conversation import Conversation
from claia.cli.settings import Settings
from claia.cli.defaults import initialize_defaults
from claia.cli.logger import initialize_logging
from claia.tools.manager import ToolsManager
from claia.tools.registry import ToolsRegistry
# from claia.cli.mod import initialize_module_system



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

# Inlined tool processing singletons
tools_manager = ToolsManager()
tools_registry = ToolsRegistry(tools_manager)



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
#                            TOOL FUNCTIONS                            #
########################################################################
def has_tool_call_tokens(content: str, conversation: Conversation) -> bool:
  """Check if content contains any opening tool tokens for the conversation's pattern."""
  if not conversation.tool_pattern_name:
    return False

  try:
    tools_manager.load_all()
    pattern_plugin, pattern_info = tools_manager.get_pattern_by_name(conversation.tool_pattern_name)
    if not pattern_plugin or not pattern_info:
      logger.debug(f"Pattern '{conversation.tool_pattern_name}' not found")
      return False
    for token in getattr(pattern_info, 'opening_tokens', []) or []:
      if token in content:
        return True
    return False
  except Exception as e:
    logger.warning(f"Error checking for tool call tokens: {e}")
    return False


def process_message_content(content: str, conversation: Conversation, settings=None, **kwargs: Any) -> str:
  """Process tool calls in content according to the conversation's tool config."""
  if not conversation.tool_pattern_name or not conversation.tool_protocol_name:
    logger.debug("No tool pattern or protocol configured for conversation")
    return content
  try:
    return tools_registry.process_content(
      conversation,
      content,
      settings=settings,
      protocol_name=conversation.tool_protocol_name,
      **kwargs
    )
  except Exception as e:
    logger.error(f"Tool processing failed: {e}")
    return content


def check_and_process_if_needed(content: str, conversation: Conversation, settings=None, **kwargs: Any) -> str:
  """Check for tool tokens and process if present; otherwise return content unchanged."""
  if has_tool_call_tokens(content, conversation):
    logger.debug("Tool call tokens detected, processing...")
    return process_message_content(content, conversation, settings, **kwargs)
  return content


def process_final_message_tools(final_message, process: Process, settings: Settings) -> None:
  """Process any tool calls in the final message and update the conversation if needed."""
  if has_tool_call_tokens(final_message.content, process.conversation):
    logger.debug("Tool calls detected in final message, processing...")
    user_kwargs = settings.get_user_kwargs()
    processed_content = process_message_content(
      final_message.content,
      process.conversation,
      settings=None,
      **user_kwargs
    )

    # If content changed, update the message and display the changes
    if processed_content != final_message.content:
      print("\n[Processing tool calls...]")
      print(processed_content[len(final_message.content):], flush=True)
      # Update the message with processed content
      process.conversation.update_message(final_message.message_id, content=processed_content)



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
    # TODO: Update command registry initialization for new architecture
    # command_registry = CommandRegistry()

    # Initialize the module system (must happen after commands are initialized)
    logger.debug("Initializing module system")
    # initialize_module_system(command_registry, settings.modules_directory)

    # Initialize the agent registry and process queue
    logger.debug("Initializing agent registry and process queue")
    agent_registry = AgentRegistry()
    agent_registry.start_workers(3)  # Start 3 worker threads

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
      # TODO: Update command processing for new architecture
      # result = command_registry.run(settings.extra_args, settings)

      # if result.get_message():
      #   print(result.get_message())

      # For now, just print a message that command processing is disabled
      print(f"Command line processing temporarily disabled: {' '.join(settings.extra_args)}")

      # Exit after running the command
      logger.info("CLAIA exiting after CLI command execution")
      agent_registry.stop_workers()
      return

    logger.info("CLAIA initialization complete, entering main loop")

    # Main application loop
    result = Result()
    while not result.is_exit():
      # Initialize and clear variables
      process = None
      response = None
      new_content = None

      # Wait for user input
      user_input = get_user_input()

      # Populate command history if input is not empty
      if user_input.strip():
        logger.debug("Adding user input to history")
        readline.add_history(user_input)

      # Process user input as either a command or a query
      if user_input and user_input[0] == COMMAND_CHARACTER:
        logger.debug(f"Processing as command: {user_input[1:]}")
        # TODO: Update command processing for new architecture
        # result = command_registry.run(user_input[1:].split(), settings)
        # print(result.message)
        print(f"Command processing temporarily disabled: {user_input[1:]}")
      else:
        # Create a new conversation if one doesn't exist
        if not settings.active_conversation:
          settings.active_conversation = Conversation(
            settings.files_directory
          )

        # Set the active agent if one doesn't exist
        if not settings.active_agent:
          settings.active_agent = DEFAULT_AGENT

        user_message = settings.active_conversation.add_message(MessageRole.USER, user_input)

        # Get user kwargs from settings
        user_kwargs = settings.get_user_kwargs()

        process = Process(
          agent_type=settings.active_agent,
          conversation=settings.active_conversation,
          parameters={
            "source_preference": SourcePreference.ANY,
            "model_id": settings.active_model,
            **user_kwargs
          }
        )

        process_id = agent_registry.add_process(process)
        logger.debug(f"Process added with ID: {process_id}")

        logger.debug(f"Waiting for process to complete: {process.id}")

        # Print updates while waiting for the process to complete
        while process.status == ProcessStatus.PENDING or process.status == ProcessStatus.PROCESSING:
          # process = process_queue.get_by_id(process.id)

          if process.status == ProcessStatus.PROCESSING:
            response = process.conversation.get_latest_message()

            if response.message_id != user_message.message_id:
              if new_content and response.content and len(response.content) > len(new_content):
                print(response.content[len(new_content):], end='', flush=True)
              elif not new_content:
                print(response.content, end='', flush=True)

              new_content = response.content

          # Sleep a bit to avoid busy waiting
          time.sleep(0.1)

        logger.debug(f"Process completed: {process.id}")

        # Display the final result
        if process.status == ProcessStatus.COMPLETED:
          final_message = process.conversation.get_latest_message()
          if new_content:
            remaining_content = final_message.content[len(new_content):]
            if remaining_content:
              print(remaining_content, flush=True)
          else:
            print(final_message.content, flush=True)
          print() # Add newline after final message

          # Check for and process any tool calls in the final message
          process_final_message_tools(final_message, process, settings)

          process.conversation.save()
        elif process.status == ProcessStatus.FAILED:
          logger.error(f"Process failed: {process.error}")
          print(f"Error: {process.error}")
        elif process.status == ProcessStatus.CANCELLED:
          logger.warning(f"Process cancelled: {process.error}")
          print("Process was cancelled.")

      # Display any error messages
      if result.is_error():
        logger.debug(f"Error result: {result.get_message()}")
        print(f"Error: {result.get_message()}")

    # Display exit message
    logger.info(f"CLAIA application exiting: {result.get_message()}")

    # Stop worker threads before exiting
    agent_registry.stop_workers()

  except Exception as e:
    logger.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
    # Try to stop worker threads on error
    if 'agent_registry' in locals():
      agent_registry.stop_workers(wait=False)  # Don't wait on critical error
    sys.exit(1)



if __name__ == "__main__":
  main()

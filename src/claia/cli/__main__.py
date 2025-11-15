# TODO:
# - create an option to enable a server that serves and updates md files, and sync conversations to md files?
# - Needs a way to filter models (since there are lots) (model list partname?)
# - perhaps have the model layer compare the capabilities against the sent request, if there's content that the model doesn't support throw a warning, maybe also trim the request to the model's capabilities
# - create a new image agent that exports the images after generation
# - create a vix demo that uses a list off images to show reactions in a conversation, think emojis (this should be a tool call since it's not generating the images, thought it's an idea to train a lora and have images generated)

# - run commands from cli with optional --flags processing instead of arg=value style, for example: claia transcribe --file <audio-file>
# - create new prompts or update existing (need to move prompts to json files)
# - update system command to allow settings updates (and save to .env file?)
# - prompt doesn't apply to the active conversation (if there's an active conversation, it should apply to it)

# - add ability to rename conversations, and perhaps have ai name conversations automatically
# - Need to clean input from user and models (set gpt-4 to temperature 2 causing issues)
# - Add multi-gpu support for transformer models
# - local models aren't using model path
# - limit list of models to only ones that can be loaded with the given api keys or parameters and maybe fetch lists from supporting apis or repos

# - local models should check ram and download size and confirm resource availability?
# - local models should have flags to select cpu or gpu, or specify certain gpus or memory usage
# - local models may suggest a quantized version of the model that may fit
# - (Consider the posibility of a hybrid deployment, where model is loaded into cpu memory, but moved to gpu memory when processing requests to allow several models to run on a single machine)
# - (or perhaps there's a deployment manager, and the deployment object contains methods to move the model between cpu and gpu as needed)

# - add required_arg filtering back for the command modules
# - add arg checking in settings module (add arg checking for required_args before loading extension?)
# - switch extension loading to be guid based, and show names on console with appended guid if name conflicts, support guid or name loading if no conflicts (select first if conflicts)

# - make command input separate from actual text and scrolling (think vim) to allow interacting with AI while it's processing (things like commands to show multiple agent workers at once)
# - throw error if agent required_args aren't found, but don't filter (agents need to pass kwargs to models). Otherwise, find a way to create some kind of secret store (singleton?) to pull args from

# - use pluggy for file types?
# - double check metadata updates when adding new content to files

# - overhaul the image resize method
# - review conversation saving setup. Is it properly handled if storing in memory or db?
# - Attaching a file in the conversation should just send the path or url along with whether or not
#   it's a reference (optional), then identify and call the correct object
#   to attach the file. If a file id is passed, then validate and identify the type

# - Add an end value to message object to indicate the end of the message (for streaming)
# - Swap prompt inside of conversation to the actual prompt object (should be a reference?)
# - Add dictionary support to the prompt object
# - Clean up onboarding
# - command character by itself should show help (code exists, but never gets called)

# - BASEFILE:
#   - Add a validate function to the that verifies that everything is as
#     expected (correct subfolder, mime type, reference, exists, etc)?
#   - Make the base file more cohesive with our state emuns (Local, External/Reference, Empty, etc)
#   - Add streaming support to our save method?
# - IMAGE:
#   - Make format function more robust and the output consistent
#   - Make all format metadata setting use the format method
#   - Is format metadata even needed since we have mime type?
#   - Make mime type rely on our enum

# - add tools/commands for each module type (solver, architecture, definitions, etc)
# - add update system (with on launch invocation) for debian repo publishing


# External dependencies
import readline
import atexit
import logging
import os
import sys
import shutil
import importlib.metadata as importlib_metadata
import pyfiglet

# Internal dependencies
from claia.lib import Process
from claia.lib.results import Result
from claia.lib.enums.model import SourcePreference
from claia.lib.enums.conversation import MessageRole
from claia.lib.data import Conversation, FileSystemRepository
from claia.cli.settings import Settings
from claia.cli.commands import Commands
from claia.cli.defaults import initialize_defaults
from claia.cli.logger import initialize_logging
from claia.cli.agents import register_cli_agents
from claia.cli.utils import stream_process_response
from claia.registry import Registry



########################################################################
#                              CONSTANTS                               #
########################################################################
HISTORY_FILE = ".claia_history"
MAX_HISTORY_LEN = 1000
COMMAND_CHARACTER = ":"
INPUT_CHARACTER = ":"
DEFAULT_AGENT = "simple"
TOOL_PATTERN_NAME = "default"
TOOL_PROTOCOL_NAME = "simple"



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              FUNCTIONS                               #
########################################################################
def setup_command_history(settings: Settings) -> None:
  """Initialize readline for command history with arrow key navigation."""
  logger.debug("Setting up command history")
  try:
    # Create history file path in the files directory
    history_file = os.path.join(settings.files_directory, HISTORY_FILE)
    
    # Ensure the history file directory exists
    history_dir = os.path.dirname(history_file)
    if history_dir and not os.path.exists(history_dir):
      logger.debug(f"Creating history directory: {history_dir}")
      os.makedirs(history_dir, exist_ok=True)

    # Try to read the history file
    logger.debug(f"Reading history from file: {history_file}")
    readline.read_history_file(history_file)
    readline.set_history_length(MAX_HISTORY_LEN)
    logger.debug(f"Command history initialized with max length: {MAX_HISTORY_LEN}")
  except FileNotFoundError:
    logger.debug(f"History file not found, will create on exit: {history_file}")
  except Exception as e:
    logger.error(f"Error setting up command history: {e}")

  atexit.register(readline.write_history_file, history_file)
  logger.debug("Registered history file write on exit")


def get_user_input() -> str:
  """Get and return user input using a standardized prompt symbol."""
  logger.debug("Waiting for user input")
  return input(INPUT_CHARACTER)



########################################################################
#                             UI/UX HELPERS                            #
########################################################################
def _get_app_version() -> str:
  """Attempt to retrieve the installed package version; fallback to 'dev'."""
  try:
    return importlib_metadata.version("claia")
  except importlib_metadata.PackageNotFoundError:
    return "dev"
  except Exception:
    return "dev"


def print_header(settings: Settings) -> None:
  """Print a friendly startup banner for the interactive CLI.

  Shows application name, version, Python version, website, and quick tips.
  Uses Unicode box drawing for aesthetics; falls back to sensible widths.
  """
  try:
    cols = shutil.get_terminal_size(fallback=(80, 20)).columns
  except Exception:
    cols = 80
  width = max(60, min(100, cols))

  def line(text: str) -> str:
    inner = text[:width - 4].ljust(width - 4)
    return f"║ {inner} ║"

  title = "CLAIA"
  subtitle = "Command Line Artificial Intelligence Agent"
  ver = _get_app_version()
  pyver = sys.version.split()[0]

  print()
  # Render big-letter title above the border
  art = pyfiglet.figlet_format(title)
  for art_line in art.rstrip("\n").splitlines():
    print(art_line.center(width))

  print("╔" + ("═" * (width - 2)) + "╗")
  print(line(subtitle))
  print(line(f"Version v{ver} • Python {pyver} • https://claia.dev"))
  print(line(""))
  
  # Show active configuration
  active_model = settings.active_model or settings.default_model or "None"
  active_agent = settings.active_agent or settings.default_agent or "None"
  print(line(f"Active Model: {active_model}"))
  print(line(f"Active Agent: {active_agent}"))
  print("╟" + ("─" * (width - 2)) + "╢")
  
  # Quick start guide
  print(line("QUICK START"))
  print(line("  • Chat: Just type your message"))
  print(line(f"  • Commands: Type '{COMMAND_CHARACTER}' followed by command (e.g., '{COMMAND_CHARACTER}help')"))
  print(line(f"  • Tools: Type '{COMMAND_CHARACTER}tool' to see modules, '{COMMAND_CHARACTER}tool <module>' for tools"))
  print(line(f"  • Setup: Type '{COMMAND_CHARACTER}setup' to configure API keys"))
  print(line(f"  • Exit: Press Ctrl+C or type '{COMMAND_CHARACTER}quit'"))
  
  # Check for unset API keys and show notice if not suppressed
  if not settings.suppress_setup_notice:
    unset_keys = settings.get_unset_api_keys()
    if unset_keys:
      print("╟" + ("─" * (width - 2)) + "╢")
      print(line("⚠ Notice: Some API keys are not configured"))
      print(line(f"  Run '{COMMAND_CHARACTER}setup' to configure {len(unset_keys)} API key(s)"))
      print(line(f"  Or use '{COMMAND_CHARACTER}set suppress_setup_notice true' to hide this"))
  
  print("╚" + ("═" * (width - 2)) + "╝")
  print()


########################################################################
#                            TOOL FUNCTIONS                            #
########################################################################
def process_final_message_tools(final_message, process: Process, settings: Settings, registry: Registry) -> None:
  """Process any tool calls in the final message and update the conversation if needed."""

  # Note: Tool pattern/protocol configuration is now handled by the registry extensions
  # We simply try to process the content and let the registry handle detection
  
  # Get user configuration parameters to pass to tools
  user_kwargs = settings.get_user_kwargs()

  # Try to process tool calls in the message content
  try:
    processed_content = registry.process_content(
      process.conversation,
      final_message.content,
      settings=None,
      **user_kwargs
    )
  except Exception as e:
    logger.debug(f"No tool processing needed or failed: {e}")
    return

  # If content changed after processing, update the message and display changes
  if processed_content != final_message.content:
    print("\n[Processing tool calls...]")
    # Display only the new content that was added (tool results)
    print(processed_content[len(final_message.content):], flush=True)
    # Update the stored message with the processed content (thread-safe)
    process.conversation.update_message(final_message.message_id, content=processed_content)


def setup_conversation(settings: Settings, registry: Registry) -> None:
  """Setup or configure the active conversation."""
  if not settings.active_conversation:
    # Create a new conversation (pure data model)
    settings.active_conversation = Conversation()



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
    user_kwargs = settings.get_user_kwargs()

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

    # Check if stdin has data (piped input)
    if not sys.stdin.isatty():
      logger.debug("Detected stdin input (piped data)")
      stdin_data = sys.stdin.read().strip()
      if stdin_data:
        logger.debug(f"Read {len(stdin_data)} characters from stdin")
        # Prepend --query to treat stdin as a query command
        settings.extra_args = ['--query', stdin_data] + settings.extra_args
        logger.info(f"Treating stdin as query command")

    # Initialize the registry
    logger.debug("Initializing unified registry")
    registry = Registry(**user_kwargs)
    _ = registry.get_commands_catalog() # NOTE: Can probably be removed later
    
    # Register CLI-specific agents using the programmatic registration API
    logger.debug("Registering CLI-specific agents")
    register_cli_agents(registry)
    
    registry.start_workers(2)  # Start n worker threads

    # Initialize command processor
    logger.debug("Initializing command processor")
    commands = Commands(registry, settings)

    # Initialize file system repository
    file_repo = FileSystemRepository(settings.files_directory)

    # Set up command history with arrow key navigation
    setup_command_history(settings)

    # Log active model, agent, and prompt information
    logger.debug(f"Active model: {settings.active_model}")
    logger.debug(f"Active agent: {settings.active_agent}")
    logger.debug(f"Active prompt: {settings.active_prompt.prompt_name if settings.active_prompt else 'None'}")

    # Check for and process command line arguments
    if settings.extra_args:
      # Process command line arguments using Commands processor
      logger.info(f"Processing command line arguments: {' '.join(settings.extra_args)}")
      # Ensure there's an active conversation for command execution context
      setup_conversation(settings, registry)

      # Execute the command using the Commands processor
      cmd_result = commands.run(settings.extra_args, settings.active_conversation, is_interactive=False)

      if cmd_result.is_success():
        data = cmd_result.get_data()
        if data is not None:
          print(data)
      else:
        print(f"Error: {cmd_result.get_message()}")

      # Check if command requested exit
      if cmd_result.is_exit():
        logger.info(f"CLAIA exiting: {cmd_result.get_message()}")
        registry.stop_workers()
        sys.exit(cmd_result.get_exit_code())

      # Exit after running the command
      logger.info("CLAIA exiting after CLI command execution")
      registry.stop_workers()
      return

    logger.info("CLAIA initialization complete, entering main loop")
    # Show a friendly header only for interactive mode
    print_header(settings)

    # Main application loop
    result = Result()
    while not result.is_exit():
      process = None

      # Wait for user input
      user_input = get_user_input()

      # Process user input as either a command or a query
      if user_input and user_input[0] == COMMAND_CHARACTER:
        logger.debug(f"Processing as command: {user_input[1:]}")
        # Process interactive command using Commands processor
        tokens = user_input[1:].split()
        
        # If no command entered, show help
        if not tokens:
          setup_conversation(settings, registry)
          cmd_result = commands.run(['help'], settings.active_conversation, is_interactive=True)
          if cmd_result.is_exit():
            result = cmd_result
          continue
        
        # Ensure there is a conversation context
        setup_conversation(settings, registry)
        
        # Execute the command using the Commands processor
        cmd_result = commands.run(tokens, settings.active_conversation, is_interactive=True)
        
        if cmd_result.is_success():
          data = cmd_result.get_data()
          if data is not None:
            print(data)
        else:
          print(f"Error: {cmd_result.get_message()}")
        
        # Check if command requested exit and terminate the main loop
        if cmd_result.is_exit():
          result = cmd_result
      else:
        # Create a new conversation if one doesn't exist
        setup_conversation(settings, registry)

        # Set the active agent if one doesn't exist
        if not settings.active_agent:
          settings.active_agent = settings.default_agent or DEFAULT_AGENT

        user_message = settings.active_conversation.add_message(MessageRole.USER, user_input)

        process = Process(
          agent_type=settings.active_agent,
          conversation=settings.active_conversation,
          parameters={
            "source_preference": SourcePreference.ANY,
            "model_id": settings.active_model,
            **user_kwargs
          }
        )

        process_id = registry.add_process(process)
        logger.debug(f"Process added with ID: {process_id}")

        logger.debug(f"Waiting for process to complete: {process.id}")

        # Stream the response and handle completion
        stream_process_response(
          process=process,
          user_message_id=user_message.message_id,
          file_repo=file_repo,
          save_conversation=True
        )

      # Display any error messages
      if result.is_error():
        logger.debug(f"Error result: {result.get_message()}")
        print(f"Error: {result.get_message()}")

    # Display exit message
    logger.info(f"CLAIA application exiting: {result.get_message()}")

    # Stop worker threads before exiting
    registry.stop_workers()

  except Exception as e:
    logger.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
    # Try to stop worker threads on error
    if 'registry' in locals():
      registry.stop_workers(wait=False)  # Don't wait on critical error
    sys.exit(1)



if __name__ == "__main__":
  main()

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

# - add required_arg filtering back for the command modules


# External dependencies
import readline
import atexit
import time
import logging
import os
import sys
import json
from typing import Optional, Dict, Any

# Internal dependencies
from claia.lib import Process
from claia.lib.results import Result
from claia.lib.enums.agent import ProcessStatus, SourcePreference
from claia.lib.enums.conversation import MessageRole
from claia.lib.files.conversation import Conversation
from claia.cli.settings import Settings
from claia.cli.defaults import initialize_defaults
from claia.cli.logger import initialize_logging
from claia.tools_registry import ToolsRegistry
from claia.agent_registry import AgentRegistry



########################################################################
#                              CONSTANTS                               #
########################################################################
HISTORY_FILE = ".claia_history"
MAX_HISTORY_LEN = 1000
COMMAND_CHARACTER = ":"
INPUT_CHARACTER = ":"
DEFAULT_AGENT = "simple"
# Default tool-calling configuration
TOOL_PATTERN_NAME = "default"
TOOL_PROTOCOL_NAME = "simple"



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
#                            TOOL FUNCTIONS                            #
########################################################################
def process_final_message_tools(final_message, process: Process, settings: Settings, tools_registry: ToolsRegistry) -> None:
  """Process any tool calls in the final message and update the conversation if needed."""

  # Step 1: Check if the conversation has a tool pattern configured
  if not process.conversation.tool_pattern_name:
    return

  # Step 2: Lightweight precheck using the registry
  try:
    has_tool_tokens = tools_registry.contains_tool_tokens(
      final_message.content,
      pattern_name=process.conversation.tool_pattern_name
    )
    if not has_tool_tokens:
      return
  except Exception as e:
    logger.warning(f"Error checking for tool call tokens: {e}")
    return

  logger.debug("Tool calls detected in final message, processing...")

  # Step 3: Verify conversation has both pattern and protocol configured
  # Protocol defines how to execute the tools (e.g., local execution, API calls)
  if not process.conversation.tool_protocol_name:
    logger.debug("No tool protocol configured for conversation")
    return

  # Step 4: Get user configuration parameters to pass to tools
  # This includes API keys, preferences, and other user-specific settings
  user_kwargs = settings.get_user_kwargs()

  # Step 5: Process the tool calls in the message content
  try:
    processed_content = tools_registry.process_content(
      process.conversation,
      final_message.content,
      settings=None,
      protocol_name=process.conversation.tool_protocol_name,
      **user_kwargs
    )
  except Exception as e:
    logger.error(f"Tool processing failed: {e}")
    return

  # Step 6: If content changed after processing, update the message and display changes
  # This happens when tool calls are replaced with their results
  if processed_content != final_message.content:
    print("\n[Processing tool calls...]")
    # Display only the new content that was added (tool results)
    print(processed_content[len(final_message.content):], flush=True)
    # Update the stored message with the processed content
    process.conversation.update_message(final_message.message_id, content=processed_content)

def ensure_tool_prompt(conv: Conversation, tools_registry: ToolsRegistry) -> None:
  """Ensure the conversation has a tool_calling_prompt set from the active pattern.

  If conv.tool_calling_prompt is empty, try to fetch the selected pattern's
  prompt_template and assign it. This wires pattern-provided prompts into
  Conversation.get_system_prompt().
  """
  if not conv:
    return
  if getattr(conv, 'tool_calling_prompt', None):
    return
  pattern_name = getattr(conv, 'tool_pattern_name', None)
  try:
    plugin, info = tools_registry.manager.get_pattern_by_name(pattern_name) if pattern_name else (None, None)
    if not plugin:
      plugin = tools_registry.manager.get_default_pattern()
      info = plugin.get_pattern_info() if plugin else None
  except Exception:
    plugin, info = None, None
  prompt = getattr(info, 'prompt_template', None) if info else None
  if prompt:
    conv.set_tool_calling_prompt(prompt)

def setup_conversation(settings: Settings, tools_registry: ToolsRegistry) -> None:
  """Setup or configure the active conversation with tool defaults if needed."""
  if not settings.active_conversation:
    settings.active_conversation = Conversation(
      settings.files_directory,
      tool_pattern_name=TOOL_PATTERN_NAME,
      tool_protocol_name=TOOL_PROTOCOL_NAME
    )
    ensure_tool_prompt(settings.active_conversation, tools_registry)
  else:
    # Backfill defaults if missing
    if not settings.active_conversation.tool_pattern_name:
      settings.active_conversation.set_tool_pattern_name(TOOL_PATTERN_NAME)
    if not settings.active_conversation.tool_protocol_name:
      settings.active_conversation.set_tool_protocol_name(TOOL_PROTOCOL_NAME)
    ensure_tool_prompt(settings.active_conversation, tools_registry)

def parse_kv_args(tokens: list[str]) -> Dict[str, Any]:
  """Parse a list of key=value tokens into a dict."""
  params: Dict[str, Any] = {}
  for tok in tokens:
    if '=' in tok:
      k, v = tok.split('=', 1)
      params[k.strip()] = v.strip()
  return params



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

    # Initialize the tools registry
    logger.debug("Initializing tools registry")
    tools_registry = ToolsRegistry()
    _ = tools_registry.get_commands_catalog() # NOTE: Can probably be removed later

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
      # Process command line arguments using ToolsRegistry
      logger.info(f"Processing command line arguments: {' '.join(settings.extra_args)}")
      # Ensure there's an active conversation for command execution context
      setup_conversation(settings, tools_registry)

      user_kwargs = settings.get_user_kwargs()
      cmd = settings.extra_args[0]
      # Build params from key=value and collect positionals into __args__
      tail_tokens = settings.extra_args[1:]
      params = parse_kv_args(tail_tokens)
      pos_args = [t for t in tail_tokens if '=' not in t]
      if pos_args:
        params['__args__'] = pos_args
      cmd_result = tools_registry.run_command(cmd, params, settings.active_conversation, **user_kwargs)

      if cmd_result.is_success():
        data = cmd_result.get_data()
        if isinstance(data, (dict, list)):
          print(json.dumps(data, indent=2))
        elif data is not None:
          print(str(data))
      else:
        print(f"Error: {cmd_result.get_message()}")

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
        # Process interactive command using ToolsRegistry
        tokens = user_input[1:].split()
        # If no command entered, print available modules
        if not tokens:
          catalog = tools_registry.get_commands_catalog()
          if not catalog:
            print("No modules available.")
          else:
            print("Available modules:")
            for mod_name, mod in catalog.items():
              info = mod.get('module_info')
              title = getattr(info, 'title', None) if info else None
              desc = getattr(info, 'description', None) if info else None
              line = f"  - {mod_name}"
              if title:
                line += f" ({title})"
              if desc:
                line += f": {desc}"
              print(line)
          continue
        cmd = tokens[0]

        # If only a module name was given, list its commands
        if '.' not in cmd and len(tokens) == 1:
          catalog = tools_registry.get_commands_catalog()
          mod = catalog.get(cmd)
          if mod:
            print(f"Module '{cmd}' commands:")
            for c in mod.get('list_of_commands', []):
              cname = c.get('command_name')
              cdesc = c.get('command_description')
              print(f"  - {cmd}.{cname}: {cdesc}")
            continue

        # Build params from key=value and collect positionals into __args__
        tail_tokens = tokens[1:]
        params = parse_kv_args(tail_tokens)
        pos_args = [t for t in tail_tokens if '=' not in t]
        if pos_args:
          params['__args__'] = pos_args
        # Ensure there is a conversation context
        setup_conversation(settings, tools_registry)
        user_kwargs = settings.get_user_kwargs()
        cmd_result = tools_registry.run_command(cmd, params, settings.active_conversation, **user_kwargs)
        if cmd_result.is_success():
          data = cmd_result.get_data()
          if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2))
          elif data is not None:
            print(str(data))
        else:
          print(f"Error: {cmd_result.get_message()}")
      else:
        # Create a new conversation if one doesn't exist
        setup_conversation(settings, tools_registry)

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
          process_final_message_tools(final_message, process, settings, tools_registry)

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

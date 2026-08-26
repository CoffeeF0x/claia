# TODO:
# - create an option to enable a server that serves and updates md files, and sync conversations to md files?
# - perhaps have the model layer compare the capabilities against the sent request, if there's content that the model doesn't support throw a warning, maybe also trim the request to the model's capabilities
# - create a new image agent that exports the images after generation
# - create a vix demo that uses a list off images to show reactions in a conversation, think emojis (this should be a tool call since it's not generating the images, thought it's an idea to train a lora and have images generated)

# - run commands from cli with optional --flags processing instead of arg=value style, for example: claia transcribe --file <audio-file>
# - create new prompts or update existing (need to move prompts to json files)
# - update system command to allow settings updates (and save to .env file?)
# - have ai name conversations automatically?
# - Need to clean input from user and models (set gpt-4 to temperature 2 causing issues)
# - Add multi-gpu support for transformer models
# - local models aren't using model path
# - limit list of models to only ones that can be loaded with the given api keys or parameters and maybe fetch lists from supporting apis or repos

# - local models should check ram and download size and confirm resource availability?
# - local models should have flags to select cpu or gpu, or specify certain gpus or memory usage
# - local models may suggest a quantized version of the model that may fit
# - (Consider the posibility of a hybrid deployment, where model is loaded into cpu memory, but moved to gpu memory when processing requests to allow several models to run on a single machine)
# - (or perhaps there's a deployment manager, and the deployment object contains methods to move the model between cpu and gpu as needed)

# - add ParamSpec-backed filtering for the command modules
# - add arg checking in settings module (validate required INIT ParamSpecs before loading extension?)
# - switch extension loading to be guid based, and show names on console with appended guid if name conflicts, support guid or name loading if no conflicts (select first if conflicts)

# - make command input separate from actual text and scrolling (think vim) to allow interacting with AI while it's processing (things like commands to show multiple agent workers at once)
# - throw error if required INIT ParamSpecs aren't provided to an agent, but don't filter (agents need to pass kwargs to models). Otherwise, find a way to create some kind of secret store (singleton?) to pull args from

# - use entry-point plugins for file types?
# - double check metadata updates when adding new content to files

# - overhaul the image resize method
# - review conversation saving setup. Is it properly handled if storing in memory or db?
# - Attaching a file in the conversation should just send the path or url along with whether or not
#   it's a reference (optional), then identify and call the correct object
#   to attach the file. If a file id is passed, then validate and identify the type

# - Add an end value to message object to indicate the end of the message (for streaming)
# - Clean up onboarding

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

# - add tools/commands for each module type (architecture, definitions, etc)
# - add update system (with on launch invocation) for debian repo publishing
# - model_id in task parameters being ignored? Bob's code example doesn't work


# External dependencies
import logging
import os
import sys
from typing import List, Optional, Tuple

# Internal dependencies
from ..core.results import Result
from ..framework.registry import Registry
from .settings import Settings
from .commands import Commands
from .defaults import initialize_defaults
from .logger import initialize_logging
from .agents import register_cli_agents



########################################################################
#                              CONSTANTS                               #
########################################################################
USAGE_LINE = "usage: claia <command> [args…]  (see 'claia help')"
HELP_POINTER = (
  "Run 'claia <command> [args…]' — e.g. claia query \"hello\", "
  "or pipe text in: echo \"hello\" | claia"
)



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               DISPATCH                               #
########################################################################
def resolve_invocation(
  args: List[str],
  stdin_tty: bool,
  stdin_data: Optional[str],
  term: Optional[str] = None,
) -> Tuple[str, List[str]]:
  """Map startup inputs to a dispatch action.

  Returns ``(action, tokens)`` where action is one of:

  - ``"run"`` — execute ``tokens`` as a one-shot command; piped
    stdin becomes an implicit leading query.
  - ``"tui"`` — no input on a terminal: launch the full-screen app.
  - ``"help"`` — no input on a terminal that cannot host the app
    (``TERM=dumb``): print help and a pointer.
  - ``"usage"`` — no input and no terminal: usage error, exit
    non-zero.
  """
  tokens = list(args)
  if not stdin_tty and stdin_data:
    tokens = ['--query', stdin_data] + tokens
  if tokens:
    return ("run", tokens)
  if stdin_tty:
    if term == "dumb":
      return ("help", [])
    return ("tui", [])
  return ("usage", [])


def result_exit_code(result: Result) -> int:
  """Process exit code for a command result; failures are non-zero."""
  code = result.get_exit_code() if result.is_exit() else 0
  if not result.is_success() and code == 0:
    code = 1
  return code



########################################################################
#                                 MAIN                                 #
########################################################################
def main() -> None:
  """One-shot entry point: build the app, run one command, exit."""
  try:
    logger.info("Initializing CLAIA...")

    # Create registry (discovers extensions but doesn't load them yet)
    # This allows Settings to collect ParamSpec declarations from extensions
    logger.debug("Initializing registry")
    registry = Registry()

    # Create Settings with registry - extension settings are handled internally
    settings = Settings(registry=registry)
    settings.root_logger = initialize_logging(settings.log_level, settings.log_format)
    settings = initialize_defaults(settings)
    user_kwargs = settings.get_user_kwargs()

    # Now load plugins with the settings
    registry.load_plugins(**user_kwargs)

    # Register CLI-layer injectables that tools may request by name via
    # their ``ArgumentDefinition`` declarations. ``registry`` is always
    # injected from within ``run_command`` itself; the extras below let
    # tools like ``cli.help`` or ``cli.settings_get`` work identically
    # whether invoked through a command wrapper (``claia help``) or
    # directly (``claia tool cli.help``).
    from .commands.specs import COMMAND_SPECS
    registry.set_tool_context(
      settings=settings,
      command_specs=COMMAND_SPECS,
    )

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

    # Read piped stdin up front; it becomes an implicit query
    stdin_tty = sys.stdin.isatty()
    stdin_data = None
    if not stdin_tty:
      logger.debug("Detected stdin input (piped data)")
      stdin_data = sys.stdin.read().strip() or None
      if stdin_data:
        logger.info("Treating stdin as query command")

    action, tokens = resolve_invocation(
      settings.extra_args, stdin_tty, stdin_data, os.environ.get("TERM"),
    )

    if action == "usage":
      print(USAGE_LINE, file=sys.stderr)
      sys.exit(2)

    # Register CLI-specific agents using the programmatic registration API
    logger.debug("Registering CLI-specific agents")
    register_cli_agents(registry)

    registry.start_workers(2)  # Start n worker threads

    if action == "tui":
      # Lazy import: one-shot startup never pays for Textual.
      from .tui import ClaiaApp
      logger.info("Launching TUI")
      ClaiaApp(registry=registry, settings=settings).run()
      logger.info("CLAIA exiting after TUI session")
      registry.stop_workers()
      return

    # Initialize command processor
    logger.debug("Initializing command processor")
    commands = Commands(registry, settings)

    # Log active model, agent, and prompt information
    logger.debug(f"Active model: {settings.active_model}")
    logger.debug(f"Active agent: {settings.active_agent}")
    logger.debug(f"Active prompt: {settings.active_prompt.prompt_name if settings.active_prompt else 'None'}")

    if action == "help":
      tokens = ["help"]

    logger.info(f"Processing command: {' '.join(tokens)}")
    result = commands.run(tokens, settings.active_conversation)

    if result.is_success():
      data = result.get_data()
      if data is not None:
        if result.format == "markdown" and sys.stdout.isatty():
          from rich.console import Console
          from rich.markdown import Markdown
          Console().print(Markdown(str(data)))
        else:
          print(data)
    else:
      message = result.get_message()
      if message:
        print(f"Error: {message}", file=sys.stderr)

    if action == "help":
      print(HELP_POINTER)

    logger.info("CLAIA exiting after command execution")
    registry.stop_workers()

    # A downstream pipe may have closed mid-stream; flush what's
    # left into the void so the interpreter's shutdown flush cannot
    # fail (which would turn a clean run into exit code 120).
    try:
      sys.stdout.flush()
    except BrokenPipeError:
      os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())

    code = result_exit_code(result)
    if code:
      sys.exit(code)

  except Exception as e:
    logger.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
    # Try to stop worker threads on error
    if 'registry' in locals():
      registry.stop_workers(wait=False)  # Don't wait on critical error
    sys.exit(1)



if __name__ == "__main__":
  main()

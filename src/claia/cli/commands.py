"""
This module manages command processing for the CLAIA application.

It handles both CLI-style commands (with flags like -q, --quit) and interactive
commands (with simple prefixes like :q, :quit), routing them to appropriate handlers
or the registry's tool system.
"""

# External dependencies
import sys
import logging
from typing import Dict, Any, List, Optional, Tuple
import importlib.metadata as importlib_metadata

# Internal dependencies
from claia.lib.results import Result
from claia.registry import Registry


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CONSTANTS                              #
########################################################################
# Format: (cli_aliases, interactive_aliases, handler_method_name, help_text)
COMMAND_SPECS: List[Tuple[List[str], List[str], str, str]] = [
  (['-q', '--quit', '--exit'], ['q', 'quit', 'exit'], '_cmd_quit',    'Exit the application'                                           ),
  (['-h', '--help'],           ['h', 'help'],         '_cmd_help',    'Show help information including commands, modules, and settings'),
  (['-v', '--version'],        ['v', 'version'],      '_cmd_version', 'Show version information'                                       ),
  (['-t', '--tool'],           ['tool'],              '_cmd_tool',    'Execute a tool command explicitly'                              ),
]


########################################################################
#                               CLASSES                                #
########################################################################
class Commands:
  """
  Processes and executes commands for the CLAIA application.
  Handles both CLI-style flags and interactive-style commands.
  """

  def __init__(self, registry: Registry, settings: Any):
    """
    Initialize the Commands processor.

    Args:
        registry: The unified registry for tools, models, and agents
        settings: The settings object containing configuration
    """
    self.registry = registry
    self.settings = settings
    
    # Build command lookup dictionaries from COMMAND_SPECS
    self._cli_command_map: Dict[str, Tuple[str, str]] = {}  # alias -> (handler_name, help_text)
    self._interactive_command_map: Dict[str, Tuple[str, str]] = {}  # alias -> (handler_name, help_text)
    
    for cli_aliases, interactive_aliases, handler_name, help_text in COMMAND_SPECS:
      # Map CLI aliases
      for alias in cli_aliases:
        self._cli_command_map[alias] = (handler_name, help_text)
      
      # Map interactive aliases
      for alias in interactive_aliases:
        self._interactive_command_map[alias.lower()] = (handler_name, help_text)
    
    logger.debug("Commands processor initialized")


  def run(self, tokens: List[str], conversation: Optional[Any] = None, is_interactive: bool = False) -> Result:
    """
    Process and execute a command from a list of tokens.

    Args:
        tokens: List of command tokens (e.g., ['--quit'] or ['q'] or ['tool', 'arg1', 'arg2'])
        conversation: Optional conversation context for tool execution
        is_interactive: Whether this is an interactive command (affects parsing)

    Returns:
        Result object indicating success/failure and any output data
    """
    if not tokens:
      return Result(success=True)

    # Get the first token as the command
    cmd = tokens[0]
    args = tokens[1:]

    # Handle CLI-style flags (--flag or -f) when not in interactive mode
    if not is_interactive:
      result = self._process_cli_flag(cmd, args, conversation)
      if result:
        return result

    # Handle interactive-style commands
    result = self._process_interactive_command(cmd, args, conversation)
    if result:
      return result

    # If no built-in command matched, try to execute as a tool via registry
    return self._cmd_tool(tokens, conversation)


  def _process_cli_flag(self, cmd: str, args: List[str], conversation: Optional[Any]) -> Optional[Result]:
    """
    Process CLI-style flag commands (--flag or -f format).

    Args:
        cmd: The command/flag string
        args: Remaining arguments
        conversation: Optional conversation context

    Returns:
        Result if command was processed, None if not recognized
    """
    # Look up command in CLI command map
    if cmd in self._cli_command_map:
      handler_name, _ = self._cli_command_map[cmd]
      handler = getattr(self, handler_name)
      
      # Special handling for tool command which needs args
      if handler_name == '_cmd_tool':
        if not args:
          return Result(success=False, message="No tool command provided")
        return handler(args, conversation)
      
      return handler()

    return None


  def _process_interactive_command(self, cmd: str, args: List[str], conversation: Optional[Any]) -> Optional[Result]:
    """
    Process interactive-style commands (simple word format like 'quit', 'help').

    Args:
        cmd: The command string
        args: Remaining arguments
        conversation: Optional conversation context

    Returns:
        Result if command was processed, None if not recognized
    """
    cmd_lower = cmd.lower()

    # Look up command in interactive command map
    if cmd_lower in self._interactive_command_map:
      handler_name, _ = self._interactive_command_map[cmd_lower]
      handler = getattr(self, handler_name)
      
      # Special handling for tool command which needs args
      if handler_name == '_cmd_tool':
        if not args:
          return Result(success=False, message="No tool command provided")
        return handler(args, conversation)
      
      return handler()

    return None


  def _parse_kv_args(self, tokens: List[str]) -> Dict[str, Any]:
    """
    Parse a list of key=value tokens into a dict.

    Args:
        tokens: List of token strings

    Returns:
        Dictionary of parsed key-value pairs
    """
    params: Dict[str, Any] = {}
    for tok in tokens:
      if '=' in tok:
        k, v = tok.split('=', 1)
        params[k.strip()] = v.strip()
    return params


  def _cmd_tool(self, tokens: List[str], conversation: Optional[Any]) -> Result:
    """
    Execute a tool command via the registry.

    Args:
        tokens: Command tokens (first token is the tool name, rest are arguments)
        conversation: Optional conversation context

    Returns:
        Result from the tool execution
    """
    if not tokens:
      return Result(success=False, message="No command provided")

    cmd = tokens[0]
    tail_tokens = tokens[1:]

    # Build params from key=value and collect positionals into __args__
    params = self._parse_kv_args(tail_tokens)
    pos_args = [t for t in tail_tokens if '=' not in t]
    if pos_args:
      params['__args__'] = pos_args

    # Get user configuration parameters
    user_kwargs = self.settings.get_user_kwargs()

    # Execute the command via registry
    try:
      result = self.registry.run_command(cmd, params, conversation, **user_kwargs)
      return result
    except Exception as e:
      logger.error(f"Error executing command '{cmd}': {e}", exc_info=True)
      return Result(success=False, message=f"Failed to execute command: {str(e)}")


  def _cmd_quit(self) -> Result:
    """
    Handle quit/exit command by calling system.exit tool.

    Returns:
        Result with exit flag set
    """
    logger.info("Quit command received")
    
    # Get user configuration parameters
    user_kwargs = self.settings.get_user_kwargs()
    
    # Call the system.exit tool through the registry
    try:
      result = self.registry.run_command('system.exit', {}, None, **user_kwargs)
      return result
    except Exception as e:
      logger.error(f"Error calling system.exit: {e}", exc_info=True)
      # Fallback to direct exit result if system.exit fails
      return Result(success=True, message="Goodbye!", exit_code=0)


  def _cmd_help(self) -> Result:
    """
    Handle help command - displays available commands and settings.

    Returns:
        Result with help information
    """
    logger.debug("Help command received")

    # Import CONFIG_VARS to show available settings
    from claia.cli.settings import CONFIG_VARS

    help_text = []
    help_text.append("\n=== CLAIA Help ===\n")

    # Built-in Commands - generated from COMMAND_SPECS
    help_text.append("Built-in Commands:")
    help_text.append("  Interactive Mode (use after ':'):")
    for cli_aliases, interactive_aliases, handler_name, help_desc in COMMAND_SPECS:
      # Format interactive aliases nicely
      aliases_str = ', '.join(interactive_aliases)
      help_text.append(f"    {aliases_str:25s} - {help_desc}")
    help_text.append("    <module>.<tool> [args]      - Execute a specific tool")
    help_text.append("")
    
    help_text.append("  CLI Mode (use as arguments):")
    for cli_aliases, interactive_aliases, handler_name, help_desc in COMMAND_SPECS:
      # Format CLI aliases nicely
      aliases_str = ', '.join(cli_aliases)
      help_text.append(f"    {aliases_str:25s} - {help_desc}")
    help_text.append("")

    # Available Modules/Tools
    help_text.append("Available Modules:")
    catalog = self.registry.get_commands_catalog()
    if catalog:
      for mod_name, mod in catalog.items():
        info = mod.get('module_info')
        title = getattr(info, 'title', None) if info else None
        desc = getattr(info, 'description', None) if info else None
        line = f"  {mod_name}"
        if title:
          line += f" ({title})"
        if desc:
          line += f": {desc}"
        help_text.append(line)

        # List tools in this module
        tools = mod.get('list_of_tools', [])
        if tools:
          for tool in tools:
            tool_name = tool.get('tool_name')
            tool_desc = tool.get('tool_description', '')
            help_text.append(f"    - {mod_name}.{tool_name}: {tool_desc}")
    else:
      help_text.append("  No modules loaded")
    help_text.append("")

    # Configuration Settings
    help_text.append("Configuration Settings:")
    help_text.append("  Settings can be configured via:")
    help_text.append("    - Command line arguments: --setting-name value")
    help_text.append("    - Environment variables: CLAIA_SETTING_NAME=value")
    help_text.append("    - .env file (default: .env)")
    help_text.append("    - settings.json file (in files directory)")
    help_text.append("")
    help_text.append("  Available settings:")
    for var_name, default, externally_settable, help_desc in CONFIG_VARS:
      if externally_settable:
        cli_name = var_name.replace('_', '-')
        current_value = getattr(self.settings, var_name, default)
        # Don't display sensitive tokens
        if 'token' in var_name or 'api' in var_name:
          display_value = "***" if current_value and current_value != default else "(not set)"
        else:
          display_value = current_value if current_value != default else f"(default: {default})"
        help_text.append(f"    --{cli_name:30s} {help_desc}")
        help_text.append(f"      Current: {display_value}")

    output = "\n".join(help_text)
    print(output)
    return Result(success=True, data=output)


  def _cmd_version(self) -> Result:
    """
    Handle version command - displays application version.

    Returns:
        Result with version information
    """
    logger.debug("Version command received")
    try:
      version = importlib_metadata.version("claia")
    except importlib_metadata.PackageNotFoundError:
      version = "dev"
    except Exception:
      version = "unknown"

    version_text = f"CLAIA version {version}"
    version_text += f"\nPython {sys.version.split()[0]}"
    version_text += f"\nPlatform: {sys.platform}"

    print(version_text)
    return Result(success=True, data=version_text)


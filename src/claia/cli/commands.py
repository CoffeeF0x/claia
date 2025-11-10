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
from collections import defaultdict

# Internal dependencies
from claia.lib.results import Result
from claia.registry import Registry
from claia.cli.settings import CONFIG_VARS, SettingCategory


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
  (['-t', '--tool'],           ['tool'],              '_cmd_tool',    'List available modules or execute tool commands'                ),
  (['-g', '--get'],            ['get'],               '_cmd_get',     'View current settings (optionally specify setting name)'        ),
  (['-s', '--set'],            ['set'],               '_cmd_set',     'Update a setting (usage: set <key> <value> or key=value)'       ),
  (['-a', '--agent'],          ['agent'],             '_cmd_agent',   'Manage agents (usage: agent [list|<agent_name>])'               ),
  (['--setup'],                ['setup'],             '_cmd_setup',   'Interactive setup wizard for API keys and configuration'        ),
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
      
      # Special handling for commands that need args
      if handler_name == '_cmd_tool':
        return handler(args, conversation)
      elif handler_name == '_cmd_set':
        if not args:
          return Result(success=False, message="No setting provided. Usage: set <key> <value> or key=value")
        return handler(args)
      elif handler_name == '_cmd_get':
        return handler(args)
      elif handler_name == '_cmd_agent':
        return handler(args)
      
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
      
      # Special handling for commands that need args
      if handler_name == '_cmd_tool':
        return handler(args, conversation)
      elif handler_name == '_cmd_set':
        if not args:
          return Result(success=False, message="No setting provided. Usage: set <key> <value> or key=value")
        return handler(args)
      elif handler_name == '_cmd_get':
        return handler(args)
      elif handler_name == '_cmd_agent':
        return handler(args)
      
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
    If no tokens provided, displays available modules.

    Args:
        tokens: Command tokens (first token is the tool name, rest are arguments)
        conversation: Optional conversation context

    Returns:
        Result from the tool execution
    """
    if not tokens:
      # Show available modules when no command provided
      catalog = self.registry.get_commands_catalog()
      if not catalog:
        output = "No modules available."
        print(output)
        return Result(success=True, message=output)
      
      output_lines = []
      output_lines.append("\nAvailable modules:")
      for mod_name, mod in catalog.items():
        info = mod.get('module_info')
        title = getattr(info, 'title', None) if info else None
        desc = getattr(info, 'description', None) if info else None
        line = f"  - {mod_name}"
        if title:
          line += f" ({title})"
        if desc:
          line += f": {desc}"
        output_lines.append(line)
      
      output_lines.append("\nUsage:")
      output_lines.append("  :tool <module>.<tool> [args]  - Execute a tool")
      output_lines.append("  :<module>.<tool> [args]       - Execute a tool (shorthand)")
      output_lines.append("  :tool <module>                - List tools in a module")
      output_lines.append("")
      
      output = "\n".join(output_lines)
      print(output)
      return Result(success=True, data=catalog)

    cmd = tokens[0]
    tail_tokens = tokens[1:]
    
    # If only a module name was given (no dot), list its tools
    if '.' not in cmd and not tail_tokens:
      catalog = self.registry.get_commands_catalog()
      mod = catalog.get(cmd)
      if mod:
        output_lines = []
        output_lines.append(f"\nModule '{cmd}' tools:")
        for c in mod.get('list_of_tools', []):
          cname = c.get('tool_name')
          cdesc = c.get('tool_description')
          output_lines.append(f"  - {cmd}.{cname}: {cdesc}")
        output_lines.append("")
        output = "\n".join(output_lines)
        print(output)
        return Result(success=True, data=mod)
      else:
        output = f"Unknown module: {cmd}\nUse ':tool' to see available modules."
        print(output)
        return Result(success=False, message=output)

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

    # Import CONFIG_VARS and SettingCategory from settings


    help_text = []
    help_text.append("\n" + "="*70)
    help_text.append("CLAIA HELP".center(70))
    help_text.append("="*70 + "\n")
 
    # Built-in Commands - generated from COMMAND_SPECS
    help_text.append("BUILT-IN COMMANDS")
    help_text.append("-" * 70)
    help_text.append("  Interactive Mode (prefix with ':'):")
    for cli_aliases, interactive_aliases, handler_name, help_desc in COMMAND_SPECS:
      # Format interactive aliases nicely
      aliases_str = ', '.join(interactive_aliases)
      help_text.append(f"    :{aliases_str:24s} - {help_desc}")
    help_text.append("    :<module>.<tool> [args]    - Execute a specific tool")
    help_text.append("")
    
    help_text.append("  CLI Mode (command line arguments):")
    for cli_aliases, interactive_aliases, handler_name, help_desc in COMMAND_SPECS:
      # Format CLI aliases nicely
      aliases_str = ', '.join(cli_aliases)
      help_text.append(f"    {aliases_str:25s} - {help_desc}")
    help_text.append("")

    # Available Modules/Tools - MORE PROMINENT
    help_text.append("AVAILABLE TOOLS & MODULES")
    help_text.append("-" * 70)
    catalog = self.registry.get_commands_catalog()
    if catalog:
      total_tools = 0
      for mod_name, mod in catalog.items():
        info = mod.get('module_info')
        title = getattr(info, 'title', None) if info else None
        desc = getattr(info, 'description', None) if info else None
        
        # Module header
        line = f"  [{mod_name}]"
        if title:
          line += f" {title}"
        help_text.append(line)
        if desc:
          help_text.append(f"    {desc}")

        # List tools in this module
        tools = mod.get('list_of_tools', [])
        if tools:
          for tool in tools:
            tool_name = tool.get('tool_name')
            tool_desc = tool.get('tool_description', '')
            help_text.append(f"    • {mod_name}.{tool_name:20s} - {tool_desc}")
            total_tools += 1
        else:
          help_text.append(f"    (no tools available)")
        help_text.append("")
      
      help_text.append(f"  Total: {len(catalog)} module(s), {total_tools} tool(s)")
    else:
      help_text.append("  No modules loaded")
    help_text.append("")

    # Configuration Settings - More compact
    help_text.append("CONFIGURATION SETTINGS")
    help_text.append("-" * 70)
    help_text.append("  Settings can be configured via:")
    help_text.append("    • Command line: --setting-name value")
    help_text.append("    • Environment: CLAIA_SETTING_NAME=value")
    help_text.append("    • .env file (default: .env)")
    help_text.append("    • settings.json (in files directory)")
    help_text.append("")
    
    # Group settings by category using the SettingCategory enum
    categorized_settings = defaultdict(list)
    
    for var_name, default, externally_settable, category, help_desc in CONFIG_VARS:
      if externally_settable:
        cli_name = var_name.replace('_', '-')
        setting_line = f"    --{cli_name:30s} {help_desc}"
        categorized_settings[category].append(setting_line)
    
    # Display settings grouped by category in enum order
    for category in SettingCategory:
      if category in categorized_settings:
        help_text.append(f"  {category.value}:")
        help_text.extend(categorized_settings[category])
        help_text.append("")
    
    help_text.append("  Use ':h' or '--help' to see this help message anytime.")
    help_text.append("="*70)

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


  def _cmd_get(self, args: List[str]) -> Result:
    """
    Handle get command - displays current settings.

    Args:
        args: Optional list containing setting name to display

    Returns:
        Result with setting information
    """
    logger.debug("Get command received")
    
    # Build a dict of all valid setting names for validation
    valid_settings = {var_name for var_name, _, externally_settable, _, _ in CONFIG_VARS if externally_settable}
    
    if args:
      # Get specific setting
      setting_name = args[0].lower().replace('-', '_')
      
      if setting_name not in valid_settings:
        output = f"Unknown setting: {setting_name}\n"
        output += f"Use ':help' or '--help' to see available settings."
        print(output)
        return Result(success=False, message=output)
      
      value = getattr(self.settings, setting_name, None)
      
      # Find the help text for this setting
      help_text = ""
      for var_name, default, externally_settable, category, help_desc in CONFIG_VARS:
        if var_name == setting_name:
          help_text = help_desc
          break
      
      output = f"\n{setting_name}: {value}"
      if help_text:
        output += f"\n  ({help_text})"
      
      print(output)
      return Result(success=True, data={setting_name: value})
    
    else:
      # Display all settings grouped by category
      output_lines = []
      output_lines.append("\n" + "="*70)
      output_lines.append("CURRENT SETTINGS".center(70))
      output_lines.append("="*70 + "\n")
      
      # Group settings by category
      categorized = defaultdict(list)
      for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
        if externally_settable:
          value = getattr(self.settings, var_name, default)
          # Mask sensitive values (tokens)
          display_value = value
          if 'token' in var_name.lower() or 'password' in var_name.lower():
            if value and value != "":
              display_value = "***" + value[-4:] if len(value) > 4 else "***"
          
          categorized[category].append((var_name, display_value, help_text))
      
      # Display settings by category
      for category in SettingCategory:
        if category in categorized:
          output_lines.append(f"{category.value}:")
          output_lines.append("-" * 70)
          for var_name, value, help_text in categorized[category]:
            output_lines.append(f"  {var_name:30s} = {value}")
          output_lines.append("")
      
      output_lines.append("="*70)
      output = "\n".join(output_lines)
      print(output)
      return Result(success=True, data=output)


  def _cmd_set(self, args: List[str]) -> Result:
    """
    Handle set command - updates a setting and saves to file.

    Args:
        args: List of arguments (either ["key=value"] or ["key", "value"])

    Returns:
        Result indicating success/failure
    """
    logger.debug("Set command received")
    
    # Build a dict of all valid setting names for validation
    valid_settings = {}
    for var_name, default, externally_settable, category, help_text in CONFIG_VARS:
      if externally_settable:
        valid_settings[var_name] = (default, help_text)
    
    # Parse the arguments
    if len(args) == 1 and '=' in args[0]:
      # Format: key=value
      key, value = args[0].split('=', 1)
      key = key.strip().lower().replace('-', '_')
      value = value.strip()
    elif len(args) >= 2:
      # Format: key value (value may contain spaces)
      key = args[0].lower().replace('-', '_')
      value = ' '.join(args[1:])
    else:
      output = "Invalid syntax. Usage: set <key> <value> or set key=value"
      print(output)
      return Result(success=False, message=output)
    
    # Validate setting name
    if key not in valid_settings:
      output = f"Unknown setting: {key}\n"
      output += f"Use ':help' or '--help' to see available settings."
      print(output)
      return Result(success=False, message=output)
    
    # Get the default value to determine type
    default_value, help_text = valid_settings[key]
    
    # Type conversion
    try:
      if isinstance(default_value, bool):
        value = value.lower() in ('true', '1', 'yes', 'on')
      elif isinstance(default_value, int):
        value = int(value)
      # Otherwise keep as string
    except (ValueError, AttributeError) as e:
      output = f"Invalid value for {key}: {value}"
      print(output)
      return Result(success=False, message=output)
    
    # Set the value on the settings object
    old_value = getattr(self.settings, key, None)
    setattr(self.settings, key, value)
    
    # Remove from CLI sourced settings if present (so it will be saved to file)
    if key in self.settings._cli_sourced_settings:
      self.settings._cli_sourced_settings.remove(key)
    
    # Save to settings file
    try:
      self.settings._save_settings_to_file()
      
      # Display confirmation
      display_value = value
      if 'token' in key.lower() or 'password' in key.lower():
        if value and value != "":
          display_value = "***" + value[-4:] if len(value) > 4 else "***"
      
      output = f"\nSetting updated and saved:"
      output += f"\n  {key}: {old_value} -> {display_value}"
      if help_text:
        output += f"\n  ({help_text})"
      
      print(output)
      return Result(success=True, message=f"Setting '{key}' updated successfully", data={key: value})
      
    except Exception as e:
      # Revert the change if save failed
      setattr(self.settings, key, old_value)
      output = f"Failed to save setting: {str(e)}"
      print(output)
      logger.error(f"Error saving settings: {e}", exc_info=True)
      return Result(success=False, message=output)


  def _cmd_agent(self, args: List[str]) -> Result:
    """
    Handle agent command - manage active agent selection.

    Args:
        args: Optional list of arguments (empty, "list", or agent name)

    Returns:
        Result indicating success/failure
    """
    logger.debug("Agent command received")
    
    # If no args, show current active agent
    if not args:
      current_agent = self.settings.active_agent or "None"
      default_agent = self.settings.default_agent or "None"
      
      output = f"\nCurrent active agent: {current_agent}"
      output += f"\nDefault agent (from settings): {default_agent}"
      output += "\n\nUsage:"
      output += "\n  :agent list          - List all available agents"
      output += "\n  :agent <agent_name>  - Switch to specified agent"
      
      print(output)
      return Result(success=True, data={"active_agent": current_agent, "default_agent": default_agent})
    
    # If "list" argument, show available agents
    if args[0].lower() == "list":
      try:
        # Get all registered agents from the manager
        agents_info = self.registry.manager.get_agents()
        
        if not agents_info:
          output = "No agents available."
          print(output)
          return Result(success=False, message=output)
        
        output_lines = []
        output_lines.append("\nAvailable Agents:")
        output_lines.append("-" * 70)
        
        for agent_info in agents_info:
          agent_name = agent_info.name
          description = getattr(agent_info, 'description', 'No description available')
          
          # Mark the current active agent
          marker = " (active)" if agent_name == self.settings.active_agent else ""
          marker += " (default)" if agent_name == self.settings.default_agent else ""
          
          output_lines.append(f"  • {agent_name}{marker}")
          output_lines.append(f"    {description}")
        
        output_lines.append("")
        output = "\n".join(output_lines)
        print(output)
        return Result(success=True, data={"agents": [info.name for info in agents_info]})
        
      except Exception as e:
        output = f"Error listing agents: {str(e)}"
        print(output)
        logger.error(f"Error listing agents: {e}", exc_info=True)
        return Result(success=False, message=output)
    
    # Otherwise, treat first arg as agent name to switch to
    agent_name = args[0].lower()
    
    # Validate that the agent exists
    try:
      agent_class = self.registry.get_agent_class(agent_name)
      
      if not agent_class:
        output = f"Unknown agent: {agent_name}"
        output += "\nUse ':agent list' to see available agents."
        print(output)
        return Result(success=False, message=output)
      
      # Set the active agent (runtime only, not persisted)
      old_agent = self.settings.active_agent
      self.settings.active_agent = agent_name
      
      output = f"\nActive agent changed: {old_agent or 'None'} -> {agent_name}"
      output += "\n(Note: This change is for the current session only)"
      output += f"\nTo set as default for future sessions, use: :set default_agent {agent_name}"
      
      print(output)
      return Result(success=True, message=f"Switched to agent '{agent_name}'", data={"agent": agent_name})
      
    except Exception as e:
      output = f"Error switching to agent '{agent_name}': {str(e)}"
      print(output)
      logger.error(f"Error switching agent: {e}", exc_info=True)
      return Result(success=False, message=output)


  def _cmd_setup(self) -> Result:
    """
    Handle setup command - interactive wizard for configuring API keys.

    Returns:
        Result indicating success/failure
    """
    logger.debug("Setup command received")
    
    print("\n" + "="*70)
    print("CLAIA SETUP WIZARD".center(70))
    print("="*70 + "\n")
    
    # Get list of unset API keys
    unset_keys = self.settings.get_unset_api_keys()
    
    if not unset_keys:
      print("✓ All API keys are configured!")
      print("\nYou can still update any settings using:")
      print("  :set <key> <value>  or  :get <key>\n")
      return Result(success=True, message="All API keys already configured")
    
    print("The following API keys are not configured:\n")
    for i, (var_name, help_text) in enumerate(unset_keys, 1):
      print(f"  {i}. {help_text} ({var_name})")
    
    print("\n" + "-"*70)
    print("\nYou can configure API keys in several ways:")
    print("  1. Interactively now (recommended for getting started)")
    print("  2. Using the ':set' command (e.g., :set openai_api_token YOUR_KEY)")
    print("  3. Setting environment variables (e.g., CLAIA_OPENAI_API_TOKEN)")
    print("  4. Adding them to your .env file")
    print("\n" + "-"*70)
    
    # Ask if user wants to configure keys now
    try:
      response = input("\nWould you like to configure API keys now? [y/N]: ").strip().lower()
      
      if response not in ('y', 'yes'):
        print("\nSetup cancelled. You can run ':setup' again anytime.")
        print("To suppress this notice on startup, run:")
        print("  :set suppress_setup_notice true\n")
        return Result(success=True, message="Setup cancelled by user")
      
      print()
      configured_count = 0
      
      # Iterate through each unset key and prompt for value
      for var_name, help_text in unset_keys:
        print(f"\n{help_text} ({var_name}):")
        print("  (Press Enter to skip)")
        
        try:
          value = input("  Value: ").strip()
          
          if value:
            # Set the value using the existing set logic
            old_value = getattr(self.settings, var_name, "")
            setattr(self.settings, var_name, value)
            
            # Remove from CLI sourced settings if present
            if var_name in self.settings._cli_sourced_settings:
              self.settings._cli_sourced_settings.remove(var_name)
            
            # Mask display for security
            display_value = "***" + value[-4:] if len(value) > 4 else "***"
            print(f"  ✓ Set {var_name} to {display_value}")
            configured_count += 1
          else:
            print(f"  ⊘ Skipped {var_name}")
            
        except (KeyboardInterrupt, EOFError):
          print("\n\nSetup interrupted.")
          break
      
      # Save all configured settings
      if configured_count > 0:
        try:
          self.settings._save_settings_to_file()
          print(f"\n✓ Successfully configured {configured_count} API key(s)!")
        except Exception as e:
          print(f"\n✗ Error saving settings: {e}")
          logger.error(f"Error saving settings during setup: {e}", exc_info=True)
          return Result(success=False, message="Failed to save settings")
      
      print("\n" + "="*70)
      print("Setup complete! You can now use CLAIA with your configured APIs.")
      print("="*70 + "\n")
      
      return Result(success=True, message=f"Configured {configured_count} API key(s)")
      
    except (KeyboardInterrupt, EOFError):
      print("\n\nSetup cancelled.")
      return Result(success=True, message="Setup cancelled by user")


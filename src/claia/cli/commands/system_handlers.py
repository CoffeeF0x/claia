"""
System command handlers for the CLAIA CLI.

This module contains handlers for system-level commands like quit, help, and version.
"""

import sys
import logging
import importlib.metadata as importlib_metadata
from collections import defaultdict

from claia.lib.results import Result
from claia.cli.settings import CONFIG_VARS, SettingCategory
from .specs import COMMAND_SPECS, generate_cli_alias


logger = logging.getLogger(__name__)


class SystemCommandsMixin:
  """Mixin class containing system command handlers."""

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
    Shows only the relevant command format based on current mode.

    Returns:
        Result with help information
    """
    logger.debug("Help command received")

    help_text = []
    help_text.append("\n" + "="*70)
    help_text.append("CLAIA HELP".center(70))
    help_text.append("="*70 + "\n")
 
    # Built-in Commands - show only the format appropriate for current mode
    help_text.append("BUILT-IN COMMANDS")
    help_text.append("-" * 70)
    
    if self._current_mode == 'interactive':
      # Interactive mode - show only colon-prefixed commands
      help_text.append("  Commands (prefix with ':'):")
      for aliases, handler_name, help_desc, needs_args, needs_conversation in COMMAND_SPECS:
        aliases_str = ', '.join(aliases)
        help_text.append(f"    :{aliases_str:24s} - {help_desc}")
      help_text.append("")
    else:
      # CLI mode - show only dash-prefixed flags
      help_text.append("  Command Line Flags:")
      for aliases, handler_name, help_desc, needs_args, needs_conversation in COMMAND_SPECS:
        cli_aliases = [generate_cli_alias(alias) for alias in aliases]
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

    # Configuration Settings - Mode-aware display
    help_text.append("CONFIGURATION SETTINGS")
    help_text.append("-" * 70)
    help_text.append("  Settings can be configured via:")
    
    if self._current_mode == 'interactive':
      # Interactive mode - show how to use :get and :set commands
      help_text.append("    • Interactive commands: :get <setting> or :set <setting> <value>")
      help_text.append("    • Command line: --setting-name value (when launching)")
      help_text.append("    • Environment: CLAIA_SETTING_NAME=value")
      help_text.append("    • .env file (default: .env)")
      help_text.append("    • settings.json (in files directory)")
      help_text.append("")
      help_text.append("  Use ':get' to view current values, ':set <name> <value>' to change.")
    else:
      # CLI mode - show command line flag usage
      help_text.append("    • Command line: --setting-name value")
      help_text.append("    • Environment: CLAIA_SETTING_NAME=value")
      help_text.append("    • .env file (default: .env)")
      help_text.append("    • settings.json (in files directory)")
      help_text.append("")
      help_text.append("  Note: the settings below are not saved to the settings.json file.")
      help_text.append("        please use one of the other methods to save your settings.")
    help_text.append("")
    
    # Group settings by category using the SettingCategory enum
    categorized_settings = defaultdict(list)
    
    for var_name, default, externally_settable, category, help_desc in CONFIG_VARS:
      if externally_settable:
        if self._current_mode == 'interactive':
          # Interactive mode - show plain setting names
          setting_line = f"    {var_name:30s} {help_desc}"
        else:
          # CLI mode - show dash-prefixed flags
          cli_name = var_name.replace('_', '-')
          setting_line = f"    --{cli_name:30s} {help_desc}"
        categorized_settings[category].append(setting_line)
    
    # Display settings grouped by category in enum order
    for category in SettingCategory:
      if category in categorized_settings:
        help_text.append(f"  {category.value}:")
        help_text.extend(categorized_settings[category])
        help_text.append("")
    
    # Show appropriate help command for the current mode
    if self._current_mode == 'interactive':
      help_text.append("  Use ':help' or ':h' to see this help message anytime.")
    else:
      help_text.append("  Use '--help' or '-h' to see this help message anytime.")
    help_text.append("="*70)

    output = "\n".join(help_text)
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

    return Result(success=True, data=version_text)


"""
ToolsManager loads and exposes plugin managers for:
- tool patterns
- tool protocols
- command modules
"""

import pluggy
import logging
import importlib.metadata as metadata
from typing import Dict, Optional

from .hooks import PatternHooks, ProtocolHooks, CommandModuleHooks


logger = logging.getLogger(__name__)


class ToolsManager:
  def __init__(self):
    self.pattern_pm = pluggy.PluginManager("claia_tool_patterns")
    self.pattern_pm.add_hookspecs(PatternHooks)

    self.protocol_pm = pluggy.PluginManager("claia_tool_protocols")
    self.protocol_pm.add_hookspecs(ProtocolHooks)

    self.module_pm = pluggy.PluginManager("claia_command_modules")
    self.module_pm.add_hookspecs(CommandModuleHooks)

    self._plugins_loaded = False

  def load_all(self) -> None:
    if self._plugins_loaded:
      return
    self._load_group('claia.tool_patterns', self.pattern_pm, 'pattern')
    self._load_group('claia.tool_protocols', self.protocol_pm, 'protocol')
    self._load_group('claia.command_modules', self.module_pm, 'module')
    self._plugins_loaded = True

  def _load_group(self, group: str, pm: pluggy.PluginManager, label: str) -> None:
    loaded = 0
    for ep in metadata.entry_points().select(group=group):
      try:
        cls = ep.load()
        inst = cls()
        pm.register(inst)
        loaded += 1
        logger.debug(f"Loaded {label} plugin: {ep.name} from {ep.value}")
      except Exception as e:
        logger.warning(f"Failed to load {label} plugin {ep.name}: {e}")
    if loaded == 0:
      logger.info(f"No {label} plugins found via entry points for group {group}")

  def get_protocol_by_name(self, name: str):
    self.load_all()
    for plugin in self.protocol_pm.get_plugins():
      info = plugin.get_protocol_info()
      if info and info.name == name:
        return plugin, info
    return None, None

  def get_module_by_name(self, name: str):
    self.load_all()
    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if info and info.name == name:
        return plugin, info
    return None, None

  def get_command_by_name(self, command_name: str):
    """
    Find a command by name across all loaded modules.

    Args:
        command_name: Full command name (e.g., "sample.add" or just "add")

    Returns:
        Tuple of (module_plugin, command_definition, module_info) or (None, None, None)
    """
    self.load_all()

    # Check if command name has module prefix
    if '.' in command_name:
      module_name, cmd_name = command_name.split('.', 1)
      # Look for specific module
      for plugin in self.module_pm.get_plugins():
        info = plugin.get_module_info()
        if info and info.name == module_name:
          # Check if module supports new command structure
          if hasattr(plugin, 'get_module_commands'):
            commands = plugin.get_module_commands()
            if cmd_name in commands:
              return plugin, commands[cmd_name], info
      return None, None, None

    # Search all modules for command name
    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if info:
        # Check new command structure first
        if hasattr(plugin, 'get_module_commands'):
          commands = plugin.get_module_commands()
          if command_name in commands:
            return plugin, commands[command_name], info
        # Fallback to legacy single-command modules
        elif info.name == command_name and hasattr(plugin, 'run'):
          # Create a legacy command definition
          from .hooks.module import CommandDefinition
          legacy_cmd = CommandDefinition(
            name=command_name,
            description=info.description,
            callable=plugin.run,
            arguments={}
          )
          return plugin, legacy_cmd, info

    return None, None, None

  def get_all_commands(self) -> Dict[str, Dict]:
    """
    Get all available commands in hierarchical format.

    Returns:
        Dict in format:
        {
          "module_name": {
            "list_of_commands": [
              {
                "command_name": str,
                "command_description": str,
                "command_callable": callable,
                "expected_args": list
              }, ...
            ]
          }, ...
        }
    """
    self.load_all()
    result = {}

    for plugin in self.module_pm.get_plugins():
      info = plugin.get_module_info()
      if not info:
        continue

      module_entry = {
        "module_info": info,
        "list_of_commands": []
      }

      # Check if module supports new command structure
      if hasattr(plugin, 'get_module_commands'):
        commands = plugin.get_module_commands()
        for cmd_name, cmd_def in commands.items():
          # Extract argument information from new ArgumentDefinition structure
          arguments_info = []
          if cmd_def.arguments:
            for arg_name, arg_def in cmd_def.arguments.items():
              arguments_info.append({
                "name": arg_name,
                "description": arg_def.description,
                "data_type": arg_def.data_type,
                "required": arg_def.required,
                "default_value": getattr(arg_def, 'default_value', None)
              })

          module_entry["list_of_commands"].append({
            "command_name": cmd_name,
            "command_description": cmd_def.description,
            "command_callable": cmd_def.callable,
            "arguments": arguments_info
          })
      # Fallback to legacy single-command modules
      elif hasattr(plugin, 'run'):
        module_entry["list_of_commands"].append({
          "command_name": info.name,
          "command_description": info.description,
          "command_callable": plugin.run,
          "arguments": []
        })

      result[info.name] = module_entry

    return result

  def get_pattern_by_name(self, name: str):
    self.load_all()
    for plugin in self.pattern_pm.get_plugins():
      info = plugin.get_pattern_info()
      if info and info.name == name:
        return plugin, info
    return None, None

  def get_default_pattern(self):
    self.load_all()
    # Choose the first available pattern for now
    patterns = list(self.pattern_pm.get_plugins())
    return patterns[0] if patterns else None

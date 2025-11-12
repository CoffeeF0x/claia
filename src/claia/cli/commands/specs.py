"""
Command specifications and helper functions for the CLAIA CLI.

This module defines the command specifications and utility functions used
across the command system.
"""

from typing import List, Tuple
from enum import IntEnum


class CommandPriority(IntEnum):
  """
  Command execution priority for ordering multiple commands.
  
  Lower values execute first. Commands with the same priority execute in
  the order they appear on the command line.
  """
  IMMEDIATE = 0    # help, version, quit - execute exclusively, ignore other commands
  CONFIG = 10      # set, get, agent, prompt, model, conversation - run before actions
  SETUP = 20       # setup wizard - interactive configuration
  ACTION = 30      # query, tool - execute last after configuration is set


# Format: (aliases, handler_method_name, help_text, needs_args, needs_conversation, priority)
# CLI versions are auto-generated: single letter = '-x', multi-letter = '--word'
COMMAND_SPECS: List[Tuple[List[str], str, str, bool, bool, CommandPriority]] = [
  (['q', 'quit', 'exit'], '_cmd_quit',         'Exit the application',                                            False, False, CommandPriority.IMMEDIATE),
  (['h', 'help'],         '_cmd_help',         'Show help information including commands, modules, and settings', False, False, CommandPriority.IMMEDIATE),
  (['v', 'version'],      '_cmd_version',      'Show version information',                                        False, False, CommandPriority.IMMEDIATE),
  (['t', 'tool'],         '_cmd_tool',         'List available modules or execute tool commands',                 True,  True,  CommandPriority.ACTION),
  (['g', 'get'],          '_cmd_get',          'View current settings (optionally specify setting name)',         True,  False, CommandPriority.CONFIG),
  (['s', 'set'],          '_cmd_set',          'Update a setting (usage: set <key> <value> or key=value)',        True,  False, CommandPriority.CONFIG),
  (['a', 'agent'],        '_cmd_agent',        'Manage agents',                                                   True,  False, CommandPriority.CONFIG),
  (['p', 'prompt'],       '_cmd_prompt',       'Manage prompts',                                                  True,  False, CommandPriority.CONFIG),
  (['c', 'conversation'], '_cmd_conversation', 'Manage conversations',                                            True,  False, CommandPriority.CONFIG),
  (['m', 'model'],        '_cmd_model',        'List and select models',                                          True,  False, CommandPriority.CONFIG),
  (['query'],             '_cmd_query',        'Send a one-shot query to the AI',                                 True,  False, CommandPriority.ACTION),
  (['setup'],             '_cmd_setup',        'Interactive setup wizard for API keys and configuration',         False, False, CommandPriority.SETUP),
]


def generate_cli_alias(alias: str) -> str:
  """
  Generate CLI-style alias from a simple alias.
  Single letter -> '-x', multi-letter -> '--word'
  
  Args:
      alias: Simple alias (e.g., 'q', 'quit')
  
  Returns:
      CLI-style alias (e.g., '-q', '--quit')
  """
  if len(alias) == 1:
    return f'-{alias}'
  else:
    return f'--{alias}'

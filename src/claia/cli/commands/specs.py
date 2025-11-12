"""
Command specifications and helper functions for the CLAIA CLI.

This module defines the command specifications and utility functions used
across the command system.
"""

from typing import List, Tuple


########################################################################
#                               CONSTANTS                              #
########################################################################
# Format: (aliases, handler_method_name, help_text, needs_args, needs_conversation)
# CLI versions are auto-generated: single letter = '-x', multi-letter = '--word'
COMMAND_SPECS: List[Tuple[List[str], str, str, bool, bool]] = [
  (['q', 'quit', 'exit'], '_cmd_quit',         'Exit the application',                                            False, False),
  (['h', 'help'],         '_cmd_help',         'Show help information including commands, modules, and settings', False, False),
  (['v', 'version'],      '_cmd_version',      'Show version information',                                        False, False),
  (['t', 'tool'],         '_cmd_tool',         'List available modules or execute tool commands',                 True,  True ),
  (['g', 'get'],          '_cmd_get',          'View current settings (optionally specify setting name)',         True,  False),
  (['s', 'set'],          '_cmd_set',          'Update a setting (usage: set <key> <value> or key=value)',        True,  False),
  (['a', 'agent'],        '_cmd_agent',        'Manage agents',                                                   True,  False),
  (['p', 'prompt'],       '_cmd_prompt',       'Manage prompts',                                                  True,  False),
  (['c', 'conversation'], '_cmd_conversation', 'Manage conversations',                                            True,  False),
  (['m', 'model'],        '_cmd_model',        'List and select models',                                          True,  False),
  (['setup'],             '_cmd_setup',        'Interactive setup wizard for API keys and configuration',         False, False),
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


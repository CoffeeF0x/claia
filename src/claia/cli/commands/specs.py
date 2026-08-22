"""
Command specifications for the CLAIA CLI.

Defines command specs mapping aliases to command names with metadata.
"""

from typing import List, Tuple

from ..enums import CommandPriority


# Format: (aliases, command_name, help_text, needs_args, needs_conversation, priority)
COMMAND_SPECS: List[Tuple[List[str], str, str, bool, bool, CommandPriority]] = [
  (['q', 'quit', 'exit'], 'quit',         'Exit the application',                                            False, False, CommandPriority.IMMEDIATE),
  (['h', 'help'],         'help',         'Show help information including commands, modules, and settings', False, False, CommandPriority.IMMEDIATE),
  (['v', 'version'],      'version',      'Show version information',                                        False, False, CommandPriority.IMMEDIATE),
  (['t', 'tool'],         'tool',         'List available modules or execute tool commands',                 True,  True,  CommandPriority.ACTION),
  (['g', 'get'],          'get',          'View current settings (optionally specify setting name)',         True,  False, CommandPriority.CONFIG),
  (['s', 'set'],          'set',          'Update a setting (usage: set <key> <value> or key=value)',        True,  False, CommandPriority.CONFIG),
  (['reset'],             'reset',        'Reset a setting (usage: reset <key>) or all RUNTIME settings (--runtime)', True, False, CommandPriority.CONFIG),
  (['a', 'agent'],        'agent',        'Manage agents',                                                   True,  False, CommandPriority.CONFIG),
  (['p', 'prompt'],       'prompt',       'Manage prompts',                                                  True,  False, CommandPriority.CONFIG),
  (['c', 'conversation'], 'conversation', 'Manage conversations',                                            True,  False, CommandPriority.CONFIG),
  (['m', 'model'],        'model',        'List and select models',                                          True,  False, CommandPriority.CONFIG),
  (['f', 'file', 'artifact'], 'file',     'Import, export, and list stored file artifacts',                  True,  False, CommandPriority.CONFIG),
  (['import'],            'import',       'Import an external file as an artifact',                          True,  False, CommandPriority.CONFIG),
  (['export'],            'export',       'Export a stored artifact to a local file',                        True,  False, CommandPriority.CONFIG),
  (['query'],             'query',        'Send a one-shot query to the AI',                                 True,  False, CommandPriority.ACTION),
  (['setup'],             'setup',        'Interactive setup wizard for API keys and configuration',         False, False, CommandPriority.SETUP),
]


def generate_cli_alias(alias: str) -> str:
  """Generate CLI-style alias: single letter -> '-x', multi-letter -> '--word'"""
  return f'-{alias}' if len(alias) == 1 else f'--{alias}'

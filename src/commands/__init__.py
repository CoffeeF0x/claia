"""
This module contains the command system for CLAIA.

It organizes commands into a hierarchical structure and provides a consistent
interface for command execution.
"""

# TODO:
# - refactor and simplify using argparse
#   - the cli should parse arguments as follows: GLOBAL_ARGS COMMAND COMMAND_ARGS SUBCOMMAND SUBCOMMAND_ARGS
#   - subcommand args shouldn't be available from the parent command, but parent args may be available after the subcommand
# - to simplify our setup with argparse, we'll want to add argparse values via the command decorator
# - the following values will be needed for each command:
#   - parent command (to define the tree)
#   - command name (can also be a list to define aliases)
#   - command args (not sure how to break these out)
#   - description (for function calling)
#   - help text (for argparse help)
#   - bool to enable function calling (note, function calling will be disabled if description and unique command name are not defined)
#   - parameters (for function calling, only necessary if parameters are available for the command)
# - we'll want to move the top level commands to their own file and essentially define them as a type of alias
# - build a system to convert the command name to something unique for function calling
#   - lean on the command tree structure and replace spaces with underscores
#   - to avoid confusion, especially with modules, we'll probably want to limit or prevent underscore usage for command names



# External dependencies
import logging

# Internal dependencies
from .prompts       import PromptCommand
from .conversations import ConversationCommand
from .models        import ModelCommand
from .system        import SystemCommand
from .tools         import ToolsCommand
from .massedcompute import MassedComputeCommand
from .agents        import AgentCommand
from .registry      import Registry
from results import Result
from settings import Settings

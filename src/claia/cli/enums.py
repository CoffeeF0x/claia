from enum import IntEnum


class CommandPriority(IntEnum):
  """Command execution priority for ordering multiple commands.

  Lower values execute first.
  """
  IMMEDIATE = 0    # help, version, quit - execute exclusively
  CONFIG = 10      # set, get, agent, prompt, model, conversation
  SETUP = 20       # setup wizard
  ACTION = 30      # query, tool - execute last

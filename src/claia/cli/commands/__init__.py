"""
CLAIA CLI Commands Package.

This package handles command processing for the CLAIA application:
bare subcommands (``claia model list``) and their generated flag
aliases (``--model``, ``-m``) resolve against the same spec list.

Each command type has its own dedicated class inheriting from
BaseCommand, registered in ``core.COMMAND_REGISTRY``.
"""

from .core import Commands

__all__ = ['Commands']


"""
CLAIA CLI Commands Package.

This package handles command processing for the CLAIA application.
It provides both CLI-style commands (with flags like -q, --quit) and interactive
commands (with simple prefixes like :q, :quit).

The new architecture uses a command registry pattern where each command type
has its own dedicated class inheriting from BaseCommand.
"""

from .core import Commands

__all__ = ['Commands']


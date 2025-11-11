"""
CLAIA CLI Commands Package.

This package handles command processing for the CLAIA application.
It provides both CLI-style commands (with flags like -q, --quit) and interactive
commands (with simple prefixes like :q, :quit).
"""

from .core import Commands

__all__ = ['Commands']


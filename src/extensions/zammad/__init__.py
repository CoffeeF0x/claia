"""
Zammad extensions package.

Provides API client, utilities, and command modules for Zammad.
"""

from .plugin_basic import ZammadBasicModulePlugin
from .plugin_processes import ZammadProcessesModulePlugin

__all__ = [
    "ZammadBasicModulePlugin",
    "ZammadProcessesModulePlugin",
]

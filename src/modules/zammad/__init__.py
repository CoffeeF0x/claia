"""
Zammad integration module for Claia.

This module provides functionality for interacting with the Zammad ticketing system.
"""

# Import the main command class for module registration
from .command import ZammadCommand
from .api import ZammadAPI
from .settings import ZammadSettings
from .utils import *
from .constants import *
"""
Zammad integration module for Claia
"""

from modules.zammad.api import ZammadAPI
from modules.zammad.settings import ZammadSettings, get_settings

__all__ = ["ZammadAPI", "ZammadSettings", "get_settings"]

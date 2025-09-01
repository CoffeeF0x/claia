"""
Zammad settings module for Claia.

This module provides settings management for the Zammad integration.
"""

# External dependencies
import os
import logging
from typing import Optional

# Internal dependencies
from .constants import ENV_ZAMMAD_API_TOKEN, ENV_ZAMMAD_BASE_URL



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               SETTINGS                               #
########################################################################
class ZammadSettings:
  """
  Settings for the Zammad module.

  Attributes:
    api_token (str): API token for Zammad.
    base_url (str): Base URL for Zammad API.
  """

  def __init__(self):
    self.api_token: str = ""
    self.base_url: str = ""
    self.load_from_env()

  def load_from_env(self) -> None:
    """
    Load settings from environment variables.
    """
    def strip_quotes(value: str) -> str:
      if value and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
      return value

    self.api_token = strip_quotes(os.environ.get(ENV_ZAMMAD_API_TOKEN, ""))
    self.base_url = strip_quotes(os.environ.get(ENV_ZAMMAD_BASE_URL, ""))

  def is_configured(self) -> bool:
    """
    Check if the Zammad settings are properly configured.

    Returns:
      bool: True if both API token and base URL are set, False otherwise.
    """
    return bool(self.api_token and self.base_url)

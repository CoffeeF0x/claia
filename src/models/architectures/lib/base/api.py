"""
API model base class.

This module defines the APIModel base class for all API-based model implementations.
"""

import requests
import logging
from typing import Optional, Dict

# Internal dependencies
from .base import BaseModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class APIModel(BaseModel):
  """Base class for API-based model implementations."""

  def __init__(self, model_name: str, base_url: str):
    super().__init__(model_name)
    self.base_url = base_url
    self.session = requests.Session()

  def set_api_key(self, api_key: str) -> None:
    """Set the API key for authentication."""
    self.set_custom_header("Authorization", f"Bearer {api_key}")

  def set_custom_header(self, header_name: str, header_value: str) -> None:
    """Set a custom header for authentication or other purposes."""
    self.session.headers.update({header_name: header_value})

  def request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, *args, **kwargs) -> requests.Response:
    """Make an API request with the configured session."""
    url = f"{self.base_url}/{endpoint}"
    response = self.session.request(method, url, json=data, params=params, *args, **kwargs)
    response.raise_for_status()
    return response

  def get(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
    """Make a GET request to the API."""
    return self.request("GET", endpoint, params=params)

  def post(self, endpoint: str, data: Dict, *args, **kwargs) -> requests.Response:
    """Make a POST request to the API."""
    return self.request("POST", endpoint, data=data, *args, **kwargs)

  def put(self, endpoint: str, data: Dict) -> requests.Response:
    """Make a PUT request to the API."""
    return self.request("PUT", endpoint, data=data)

  def delete(self, endpoint: str) -> requests.Response:
    """Make a DELETE request to the API."""
    return self.request("DELETE", endpoint)

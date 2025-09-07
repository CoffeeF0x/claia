"""
Zammad API client for CLAIA.

This client handles HTTP interactions with the Zammad API and returns raw data.
Formatting and higher-level processing is handled in utils.
"""

# External dependencies
import logging
import requests
import urllib.parse
from tempfile import NamedTemporaryFile
from typing import Optional, List, Dict, Any

# Optional AIA dependency for certificate handling
try:
  from aia import AIASession
except ImportError:  # pragma: no cover - optional dependency fallback
  class AIASession:
    def cadata_from_url(self, url):
      return ""

# Internal dependencies
from .constants import TICKET_QUERIES, SAFETY_LIMIT


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                              API CLASS                               #
########################################################################
class ZammadAPI:
  """Client for interacting with the Zammad API (raw data only)."""

  def __init__(self, base_url: Optional[str] = None, api_token: Optional[str] = None) -> None:
    self.base_url = base_url or ""
    self.api_token = api_token or ""
    self.headers = {
      "Authorization": f"Token token={self.api_token}" if self.api_token else "",
      "Content-Type": "application/json",
    }
    self.session = AIASession()

  def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None):
    if not self.base_url:
      raise ValueError("Zammad base_url not configured")

    url = f"{self.base_url}{endpoint}"
    cadata = self.session.cadata_from_url(url)

    with NamedTemporaryFile("w") as pem_file:
      pem_file.write(cadata)
      pem_file.flush()
      try:
        if method.lower() == 'get':
          response = requests.get(url, headers=self.headers, verify=pem_file.name)
        elif method.lower() == 'post':
          response = requests.post(url, headers=self.headers, json=data, verify=pem_file.name)
        elif method.lower() == 'delete':
          response = requests.delete(url, headers=self.headers, json=data, verify=pem_file.name)
        else:
          raise ValueError(f"Unsupported HTTP method: {method}")
        response.raise_for_status()
        return response.json() if response.content else None
      except Exception as e:
        logger.error(f"API request error ({method} {endpoint}): {str(e)}")
        raise

  # Core request helpers
  def get(self, endpoint: str):
    return self._make_request('get', endpoint)

  def post(self, endpoint: str, data: Dict[str, Any]):
    return self._make_request('post', endpoint, data)

  def delete(self, endpoint: str, data: Dict[str, Any]):
    return self._make_request('delete', endpoint, data)

  # High-level raw data methods
  def get_ticket(self, ticket_id: int | str) -> Dict[str, Any]:
    return self.get(f"tickets/{ticket_id}")

  def get_ticket_articles(self, ticket_id: int | str) -> List[Dict[str, Any]]:
    return self.get(f"ticket_articles/by_ticket/{ticket_id}")

  def search_tickets(self, query: str, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    encoded_query = urllib.parse.quote(query)
    return self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={per_page}&sort_by=updated_at&order_by=asc")

  def list_tickets(self, query_name: str = "open-tickets", limit: int = 100, full_response: bool = False) -> Optional[List[Dict[str, Any]]]:
    try:
      query = TICKET_QUERIES.get(query_name, query_name)
      page = 1
      response = self.search_tickets(query, page=page, per_page=limit)
      ticket_ids = response.get("tickets", [])
      assets = response.get("assets", {})
      tickets_count = response.get("tickets_count", 0)
      tickets: List[Dict[str, Any]] = []

      while full_response and response.get("tickets_count", 0) > 0 and page * limit < SAFETY_LIMIT:
        page += 1
        response = self.search_tickets(query, page=page, per_page=limit)
        ticket_ids.extend(response.get("tickets", []))
        # Assets structure can be merged when paging; in practice, first page has enough for listing
        more_assets = response.get("assets", {})
        if isinstance(assets, dict) and isinstance(more_assets, dict):
          for k, v in more_assets.items():
            if k in assets and isinstance(assets[k], dict) and isinstance(v, dict):
              assets[k].update(v)
            else:
              assets[k] = v
        tickets_count += response.get("tickets_count", 0)

      # Extract ticket data from assets
      if isinstance(assets, dict) and "Ticket" in assets:
        for ticket in assets["Ticket"].values():
          tickets.append(ticket)
      else:
        # Fallback: if assets missing, try fetching each ticket id (slower)
        for tid in ticket_ids:
          try:
            tickets.append(self.get_ticket(tid))
          except Exception:
            pass
      return tickets
    except Exception as e:
      logger.error(f"Error listing tickets: {str(e)}")
      return None

  def list_tags(self, ticket_id: int | str) -> List[str]:
    try:
      response = self.get(f"tags?object=Ticket&o_id={ticket_id}")
      return response.get("tags", []) if isinstance(response, dict) else []
    except Exception as e:
      logger.error(f"Error listing tags for ticket {ticket_id}: {str(e)}")
      return []

  def add_tag(self, ticket_id: int | str, tag: str) -> bool:
    data = {"item": tag, "object": "Ticket", "o_id": ticket_id}
    try:
      self.post("tags/add", data)
      return True
    except Exception as e:
      logger.error(f"Error adding tag '{tag}' to ticket {ticket_id}: {str(e)}")
      return False

  def remove_tag(self, ticket_id: int | str, tag: str) -> bool:
    data = {"item": tag, "object": "Ticket", "o_id": ticket_id}
    try:
      self.delete("tags/remove", data)
      return True
    except Exception as e:
      logger.error(f"Error removing tag '{tag}' from ticket {ticket_id}: {str(e)}")
      return False

  def delete_ticket(self, ticket_id: int | str) -> bool:
    try:
      self.delete(f"tickets/{ticket_id}", {})
      return True
    except Exception as e:
      logger.error(f"Error deleting ticket with ID {ticket_id}: {str(e)}")
      return False

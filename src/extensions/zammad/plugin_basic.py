"""
Zammad basic commands module plugin.

Provides listing, details, and basic tag/subject operations.
"""

import logging
from typing import Dict
import pluggy

from claia.hooks.tool import ToolModuleInfo, ToolDefinition, ArgumentDefinition
from .api import ZammadAPI
from .utils import ZammadUtils
from .constants import TICKET_QUERIES


hookimpl = pluggy.HookimplMarker("claia_tool_modules")
logger = logging.getLogger(__name__)


class ZammadBasicModulePlugin:
  """Plugin implementation for basic Zammad commands."""

  def __init__(self, **kwargs):
    # Required args (filtered by manager when available)
    self.zammad_api_token = kwargs.get('zammad_api_token', '')
    self.zammad_base_url = kwargs.get('zammad_base_url', '')
    self.files_directory = kwargs.get('files_directory', '')

    # Lazy init
    self._api: ZammadAPI | None = None
    self._utils: ZammadUtils | None = None

  def _get_api(self) -> ZammadAPI:
    if self._api is None:
      self._api = ZammadAPI(self.zammad_base_url, self.zammad_api_token)
    return self._api

  def _get_utils(self) -> ZammadUtils:
    if self._utils is None:
      self._utils = ZammadUtils(self._get_api())
    return self._utils

  @hookimpl
  def get_module_info(self) -> ToolModuleInfo:
    return ToolModuleInfo(
      name="zammad",
      title="Zammad Integration",
      description="Basic commands for interacting with Zammad",
      required_args=['zammad_api_token', 'zammad_base_url', 'files_directory']
    )

  @hookimpl
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    return {
      "list": ToolDefinition(
        name="list",
        description="List tickets based on a query",
        callable=self.list_tickets,
        arguments={
          "query": ArgumentDefinition(
            name="query",
            description="Query name or custom query string (default: open-tickets)",
            data_type="str",
            required=False,
            default_value="open-tickets",
          ),
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to display (default: 99)",
            data_type="int",
            required=False,
            default_value=99,
          ),
          "compact": ArgumentDefinition(
            name="compact",
            description="Show compact view without details",
            data_type="bool",
            required=False,
            default_value=False,
          ),
        },
      ),
      "details": ToolDefinition(
        name="details",
        description="Get ticket details by ID",
        callable=self.get_ticket_details,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket",
            data_type="int",
            required=True,
          ),
          "compact": ArgumentDefinition(
            name="compact",
            description="Compact view (hide full bodies)",
            data_type="bool",
            required=False,
            default_value=False,
          ),
        },
      ),
      "tag_add": ToolDefinition(
        name="tag_add",
        description="Add a tag to a ticket",
        callable=self.add_tag,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket",
            data_type="int",
            required=True,
          ),
          "tag": ArgumentDefinition(
            name="tag",
            description="Tag to add",
            data_type="str",
            required=True,
          ),
        },
      ),
      "tag_remove": ToolDefinition(
        name="tag_remove",
        description="Remove a tag from a ticket",
        callable=self.remove_tag,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket",
            data_type="int",
            required=True,
          ),
          "tag": ArgumentDefinition(
            name="tag",
            description="Tag to remove",
            data_type="str",
            required=True,
          ),
        },
      ),
      "find_subject": ToolDefinition(
        name="find_subject",
        description="Find tickets with a subject substring",
        callable=self.find_tickets_by_subject,
        arguments={
          "subject": ArgumentDefinition(
            name="subject",
            description="Subject substring to search",
            data_type="str",
            required=True,
          ),
          "limit": ArgumentDefinition(
            name="limit",
            description="Max results (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0,
          ),
        },
      ),
      "delete_subject": ToolDefinition(
        name="delete_subject",
        description="Delete tickets whose subject contains a substring (requires confirm)",
        callable=self.delete_tickets_by_subject,
        arguments={
          "subject": ArgumentDefinition(
            name="subject",
            description="The subject line to match (case-insensitive)",
            data_type="str",
            required=True,
          ),
          "confirm": ArgumentDefinition(
            name="confirm",
            description="Confirmation flag to proceed",
            data_type="bool",
            required=False,
            default_value=False,
          ),
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to process (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0,
          ),
        },
      ),
    }

  # ---------- Command implementations ----------
  def list_tickets(self, query: str = "open-tickets", limit: int = 99, compact: bool = False, **kwargs) -> str:
    try:
      api = self._get_api()
      utils = self._get_utils()
      tickets = api.list_tickets(query) or []
      return utils.format_ticket_list(tickets, query=query, limit=limit, compact=compact)
    except Exception as e:
      logger.exception(f"Error listing tickets: {str(e)}")
      return f"Error listing tickets: {str(e)}"

  def get_ticket_details(self, ticket_id: int, compact: bool = False, **kwargs) -> str:
    try:
      utils = self._get_utils()
      return utils.format_ticket_details(ticket_id, compact=compact)
    except Exception as e:
      logger.exception(f"Error getting ticket details: {str(e)}")
      return f"Error getting ticket details: {str(e)}"

  def add_tag(self, ticket_id: int, tag: str, **kwargs) -> str:
    try:
      api = self._get_api()
      if api.add_tag(ticket_id, tag):
        return f"Successfully added tag '{tag}' to ticket {ticket_id}."
      return f"Failed to add tag '{tag}' to ticket {ticket_id}."
    except Exception as e:
      logger.exception(f"Error adding tag: {str(e)}")
      return f"Error adding tag: {str(e)}"

  def remove_tag(self, ticket_id: int, tag: str, **kwargs) -> str:
    try:
      api = self._get_api()
      if api.remove_tag(ticket_id, tag):
        return f"Successfully removed tag '{tag}' from ticket {ticket_id}."
      return f"Failed to remove tag '{tag}' from ticket {ticket_id}."
    except Exception as e:
      logger.exception(f"Error removing tag: {str(e)}")
      return f"Error removing tag: {str(e)}"

  def find_tickets_by_subject(self, subject: str, limit: int = 0, **kwargs) -> str:
    try:
      utils = self._get_utils()
      matches = utils.find_tickets_by_subject(subject, limit)
      if not matches:
        return f"No tickets found with subject containing '{subject}'."
      lines = [f"Found {len(matches)} tickets with subject containing '{subject}':"]
      for t in matches:
        lines.append(f"  #{t['id']}: {t['title']}")
      return "\n".join(lines)
    except Exception as e:
      logger.exception(f"Error finding tickets: {str(e)}")
      return f"Error finding tickets: {str(e)}"

  def delete_tickets_by_subject(self, subject: str, confirm: bool = False, limit: int = 0, **kwargs) -> str:
    try:
      if not confirm:
        return f"This operation will delete tickets with subject: '{subject}'. Set confirm=True to proceed."
      api = self._get_api()
      utils = self._get_utils()
      matches = utils.find_tickets_by_subject(subject, limit)
      if not matches:
        return f"No tickets found with subject containing '{subject}'."
      deleted = 0
      for t in matches:
        try:
          if api.delete_ticket(t['id']):
            deleted += 1
        except Exception:
          logger.warning(f"Failed deleting ticket {t['id']}")
      if deleted == len(matches):
        return f"Successfully deleted all {deleted} tickets with subject containing '{subject}'."
      else:
        return f"Deleted {deleted} of {len(matches)} tickets with subject containing '{subject}'."
    except Exception as e:
      logger.exception(f"Error deleting tickets: {str(e)}")
      return f"Error deleting tickets: {str(e)}"

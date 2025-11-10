"""
Zammad process commands module plugin.

Provides AI-assisted tagging and account processing, including bulk operations.
"""

import logging
from typing import Dict
import pluggy

from claia.hooks.tool import ToolModuleInfo, ToolDefinition, ArgumentDefinition
from claia.lib.data import TextFile
from .api import ZammadAPI
from .utils import ZammadUtils


hookimpl = pluggy.HookimplMarker("claia_tool_modules")
logger = logging.getLogger(__name__)


class ZammadProcessesModulePlugin:
  """Plugin implementation for Zammad processing workflows."""

  def __init__(self, **kwargs):
    self.zammad_api_token = kwargs.get('zammad_api_token', '')
    self.zammad_base_url = kwargs.get('zammad_base_url', '')
    self.files_directory = kwargs.get('files_directory', '')

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
      name="zammad_processes",
      title="Zammad Processes",
      description="AI-assisted workflows for Zammad (tagging, account processing)",
      required_args=['zammad_api_token', 'zammad_base_url', 'files_directory']
    )

  @hookimpl
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    return {
      "process_single": ToolDefinition(
        name="process_single",
        description="Process a single ticket and add AI tags",
        callable=self.process_single_ticket,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket to process",
            data_type="int",
            required=True,
          ),
        },
      ),
      "untag_single": ToolDefinition(
        name="untag_single",
        description="Remove AI tags from a single ticket",
        callable=self.untag_single_ticket,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the ticket to untag",
            data_type="int",
            required=True,
          ),
        },
      ),
      "process_tag": ToolDefinition(
        name="process_tag",
        description="Process untagged tickets and add AI tags",
        callable=self.process_tag_tickets,
        arguments={
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to process (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0,
          ),
        },
      ),
      "process_untag": ToolDefinition(
        name="process_untag",
        description="Remove AI tags from all tagged tickets",
        callable=self.process_untag_tickets,
        arguments={
          "limit": ArgumentDefinition(
            name="limit",
            description="Maximum number of tickets to process (0 for no limit)",
            data_type="int",
            required=False,
            default_value=0,
          ),
        },
      ),
      "process_account_single": ToolDefinition(
        name="process_account_single",
        description="Process a single account management ticket",
        callable=self.process_account_single,
        arguments={
          "ticket_id": ArgumentDefinition(
            name="ticket_id",
            description="ID of the account management ticket to process",
            data_type="int",
            required=True,
          ),
          "output_file": ArgumentDefinition(
            name="output_file",
            description="File name to save/update account list",
            data_type="str",
            required=False,
            default_value="account-list.txt",
          ),
        },
      ),
      "process_account": ToolDefinition(
        name="process_account",
        description="Process account management tickets and build account list",
        callable=self.process_account_tickets,
        arguments={
          "output_file": ArgumentDefinition(
            name="output_file",
            description="File name to save/update account list",
            data_type="str",
            required=False,
            default_value="account-list.txt",
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
  def process_single_ticket(self, ticket_id: int, **kwargs) -> str:
    try:
      utils = self._get_utils()
      ok, tag_name, err = utils.tag_ticket(self.files_directory, ticket_id)
      if ok:
        return f"Ticket {ticket_id} tagged with '{tag_name}'."
      return f"Failed to process ticket {ticket_id}: {err}"
    except Exception as e:
      logger.exception(f"Error processing ticket: {str(e)}")
      return f"Error processing ticket: {str(e)}"

  def untag_single_ticket(self, ticket_id: int, **kwargs) -> str:
    try:
      utils = self._get_utils()
      count, tags = utils.untag_ticket(ticket_id)
      if count > 0:
        return f"Removed {count} AI tags from ticket {ticket_id}: {', '.join(tags)}"
      return f"No AI tags found on ticket {ticket_id}."
    except Exception as e:
      logger.exception(f"Error untagging ticket: {str(e)}")
      return f"Error untagging ticket: {str(e)}"

  def process_tag_tickets(self, limit: int = 0, **kwargs) -> str:
    try:
      api = self._get_api()
      utils = self._get_utils()
      tickets = api.list_tickets("untagged-tickets", limit=999, full_response=True) or []
      if not tickets:
        return "No untagged tickets found."
      if limit > 0:
        tickets = tickets[:limit]
      processed = 0
      for t in tickets:
        ok, tag_name, err = utils.tag_ticket(self.files_directory, t.get('id'))
        if ok:
          processed += 1
      return f"Processed {processed} of {len(tickets)} tickets."
    except Exception as e:
      logger.exception(f"Error processing tickets: {str(e)}")
      return f"Error processing tickets: {str(e)}"

  def process_untag_tickets(self, limit: int = 0, **kwargs) -> str:
    try:
      api = self._get_api()
      utils = self._get_utils()
      tickets = api.list_tickets("tagged-tickets", limit=999, full_response=True) or []
      if not tickets:
        return "No AI-tagged tickets found."
      if limit > 0:
        tickets = tickets[:limit]
      processed = 0
      for t in tickets:
        utils.untag_ticket(t.get('id'))
        processed += 1
      return f"Removed AI tags from {processed} tickets."
    except Exception as e:
      logger.exception(f"Error untagging tickets: {str(e)}")
      return f"Error untagging tickets: {str(e)}"

  def process_account_single(self, ticket_id: int, output_file: str = "account-list.txt", **kwargs) -> str:
    try:
      utils = self._get_utils()
      file = TextFile(self.files_directory, file_name=output_file)
      ok, msg, out_file = utils.process_account_ticket(self.files_directory, ticket_id, file=file)
      if ok:
        return f"Processed account ticket {ticket_id} and updated '{output_file}'."
      return f"Failed to process account ticket {ticket_id}: {msg}"
    except Exception as e:
      logger.exception(f"Error processing account ticket: {str(e)}")
      return f"Error processing account ticket: {str(e)}"

  def process_account_tickets(self, output_file: str = "account-list.txt", limit: int = 0, **kwargs) -> str:
    try:
      api = self._get_api()
      utils = self._get_utils()
      tickets = api.list_tickets("account-management", limit=999, full_response=True) or []
      if not tickets:
        return "No account-management tickets found."
      if limit > 0:
        tickets = tickets[:limit]
      file = TextFile(self.files_directory, file_name=output_file)
      processed = 0
      for t in tickets:
        ok, msg, _ = utils.process_account_ticket(self.files_directory, t.get('id'), file=file)
        if ok:
          processed += 1
      return f"Processed {processed} of {len(tickets)} account tickets. Updated '{output_file}'."
    except Exception as e:
      logger.exception(f"Error processing account tickets: {str(e)}")
      return f"Error processing account tickets: {str(e)}"

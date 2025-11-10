"""
Utilities and processors for Zammad data.

Responsible for formatting API data and orchestrating AI-assisted processes.
"""

# External dependencies
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup

# CLAIA dependencies
from claia.lib import Process
from claia.lib.queue import ProcessQueue
from claia.lib.enums.process import ProcessStatus
from claia.lib.enums.model import SourcePreference
from claia.lib.data import Conversation, TextFile
from claia.lib.enums.conversation import MessageRole

# Internal module dependencies
from .api import ZammadAPI
from .constants import TAG_LIST, TICKET_QUERIES, TIMEOUT, ACTIVE_MODEL, TAG_PROMPT, ACCOUNT_MANAGEMENT_PROMPT, VERIFICATION_PROMPT


logger = logging.getLogger(__name__)


class ZammadUtils:
  """Utility and processing helpers for Zammad."""

  def __init__(self, api: ZammadAPI):
    self.api = api

  # ---------- Text cleaning and formatting ----------
  def _clean_html_content(self, text: str) -> str:
    if not text:
      return ""
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text(separator='\n')
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text.strip())
    return clean_text

  def _extract_unique_content(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for art in articles or []:
      body = self._clean_html_content(art.get('body', ''))
      paragraphs = body.split('\n\n')
      uniq_paras: List[str] = []
      for para in paragraphs:
        normalized = re.sub(r'\s+', ' ', para.strip())
        if len(normalized) > 30 and normalized not in seen:
          seen.add(normalized)
          uniq_paras.append(para)
      if uniq_paras:
        new_art = art.copy()
        new_art['body'] = '\n\n'.join(uniq_paras)
        unique.append(new_art)
    return unique

  def _wrap_lines(self, text: str, width: int) -> List[str]:
    lines: List[str] = []
    for line in (text or '').split('\n'):
      while line and len(line) > width:
        break_point = line[:width].rfind(' ')
        if break_point == -1 or break_point < 30:
          break_point = width
        lines.append(line[:break_point])
        line = line[break_point:].lstrip()
      if line:
        lines.append(line)
    return lines

  # ---------- Public formatting helpers ----------
  def format_ticket_details(self, ticket_id: int | str, compact: bool = False) -> str:
    try:
      ticket = self.api.get_ticket(ticket_id)
      articles = self.api.get_ticket_articles(ticket_id)
      unique_articles = self._extract_unique_content(articles or [])

      width = 78
      response: List[str] = [f"┌{'─' * width}┐"]
      response.append(f"│ {'TICKET DETAILS':^{width-2}} │")
      response.append(f"├{'─' * width}┤")
      response.append(f"│ {'Ticket ID:':<15} {ticket.get('id', ''):<{width-18}} │")
      response.append(f"│ {'Number:':<15} {ticket.get('number', ''):<{width-18}} │")
      response.append(f"│ {'Title:':<15} {ticket.get('title', ''):<{width-18}} │")
      response.append(f"│ {'State:':<15} {ticket.get('state', str(ticket.get('state_id', ''))):<{width-18}} │")
      response.append(f"│ {'Priority:':<15} {ticket.get('priority', str(ticket.get('priority_id', ''))):<{width-18}} │")
      response.append(f"│ {'Created At:':<15} {ticket.get('created_at', ''):<{width-18}} │")
      response.append(f"│ {'Updated At:':<15} {ticket.get('updated_at', ''):<{width-18}} │")

      tags = ticket.get('tags', [])
      if tags:
        response.append(f"│ {'Tags:':<15} {', '.join(tags):<{width-18}} │")

      response.append(f"├{'─' * width}┤")
      response.append(f"│ {'CONVERSATION HISTORY':^{width-2}} │")
      response.append(f"├{'─' * width}┤")

      if not unique_articles:
        response.append(f"│ {'No conversation history found':^{width-2}} │")
        response.append(f"└{'─' * width}┘")
        return "\n".join(response)

      for i, article in enumerate(unique_articles):
        response.append(f"│ {'Message #' + str(i+1):^{width-2}} │")
        response.append(f"├{'─' * width}┤")
        response.append(f"│ {'From:':<10} {article.get('from', 'Unknown'):<{width-13}} │")
        if article.get('to'):
          response.append(f"│ {'To:':<10} {article.get('to', ''):<{width-13}} │")
        if article.get('cc'):
          response.append(f"│ {'CC:':<10} {article.get('cc', ''):<{width-13}} │")
        response.append(f"│ {'Subject:':<10} {article.get('subject', ''):<{width-13}} │")
        response.append(f"│ {'Date:':<10} {article.get('created_at', ''):<{width-13}} │")
        response.append(f"├{'─' * width}┤")

        body = article.get('body', '')
        if compact:
          if body:
            preview = body.replace('\n', ' ').strip()[:100]
            if len(body) > 100:
              preview += '...'
            response.append(f"│ {preview:<{width-2}} │")
        else:
          if body:
            for line in self._wrap_lines(body, width-4):
              response.append(f"│ {line:<{width-2}} │")
          else:
            response.append(f"│ {'(No content)':<{width-2}} │")

        if i < len(unique_articles) - 1:
          response.append(f"├{'─' * width}┤")
        else:
          response.append(f"└{'─' * width}┘")

      if compact:
        response.append("\nTo view full message bodies:")
        response.append(f"claia zammad details {ticket_id}")
      else:
        response.append("\nFor a more compact view:")
        response.append(f"claia zammad details {ticket_id} --compact")

      return "\n".join(response)
    except Exception as e:
      logger.error(f"Error formatting ticket details: {str(e)}")
      return f"Error getting ticket details: {str(e)}"

  def format_ticket_list(self, tickets: List[Dict[str, Any]], query: str, limit: int = 99, compact: bool = False) -> str:
    total_tickets = len(tickets or [])
    shown_tickets = tickets[:limit] if limit > 0 else tickets

    # Constants for formatting
    width = 100
    
    response = []
    response.append("┌" + "─" * width + "┐")
    response.append("│" + "ZAMMAD TICKETS".center(width) + "│")
    response.append("├" + "─" * width + "┤")
    
    # Query information
    query_display = f"{query} ({TICKET_QUERIES[query]})" if query in TICKET_QUERIES else query
    response.append(f"│ Query: {query_display:<{width - 9}} │")
    response.append(f"│ Found {total_tickets} tickets, showing {len(shown_tickets)}{'':<{width - 26 - len(str(total_tickets)) - len(str(len(shown_tickets)))}} │")
    response.append("├" + "─" * width + "┤")

    if not shown_tickets:
      response.append("│" + "No tickets found".center(width) + "│")
      response.append("└" + "─" * width + "┘")
      return '\n'.join(response)

    if compact:
      # Compact mode: Simple list format
      for ticket in shown_tickets:
        ticket_id = str(ticket.get('id', 'N/A'))
        title = ticket.get('title', 'Unknown')
        
        # Calculate available space for title
        # Format: "│ #ID - TITLE │"
        prefix = f"│ #{ticket_id} - "
        suffix = " │"
        available_width = width - len(prefix) - len(suffix)
        
        if len(title) > available_width:
          title = title[:available_width - 3] + "..."
        
        response.append(f"{prefix}{title:<{available_width}}{suffix}")
    else:
      # Full table mode with proper alignment
      # Column widths
      id_width = 8
      title_width = 45
      created_width = 20
      state_width = width - id_width - title_width - created_width - 11  # 7 for separators
      
      # Header
      header = f"│ {'ID':<{id_width}} │ {'TITLE':<{title_width}} │ {'CREATED':<{created_width}} │ {'STATE':<{state_width}} │"
      response.append(header)
      response.append("├─" + "─" * id_width + "─┼─" + "─" * title_width + "─┼─" + "─" * created_width + "─┼─" + "─" * state_width + "─┤")
      
      # Rows
      for ticket in shown_tickets:
        ticket_id = str(ticket.get('id', 'N/A'))
        title = ticket.get('title', 'Unknown')
        created_at = ticket.get('created_at', '')
        state = ticket.get('state', {})
        
        # Truncate title if too long
        if len(title) > title_width:
          title = title[:title_width - 3] + "..."
        
        # Format created date
        if isinstance(created_at, str) and len(created_at) >= 16:
          created_str = created_at[:16]
        else:
          created_str = str(created_at)[:created_width]
        
        # Get state name
        if isinstance(state, dict):
          state_name = state.get('name', 'Unknown')
        else:
          state_name = str(state)
        
        # Truncate state if too long
        if len(state_name) > state_width:
          state_name = state_name[:state_width - 3] + "..."
        
        row = f"│ {ticket_id:<{id_width}} │ {title:<{title_width}} │ {created_str:<{created_width}} │ {state_name:<{state_width}} │"
        response.append(row)

    response.append("└" + "─" * width + "┘")
    return '\n'.join(response)

  # ---------- AI-assisted processors ----------
  def extract_tag(self, response: str) -> Tuple[str, bool]:
    if not response:
      return "Blank", False
    cleaned = response.replace("\\", "")
    try:
      if "[TAG]" in cleaned and "[/TAG]" in cleaned:
        start = cleaned.index("[TAG]") + len("[TAG]")
        end = cleaned.index("[/TAG]")
        tag = cleaned[start:end].strip()
        if tag in TAG_LIST:
          return tag, True
        else:
          return "Unknown", False
      return "Blank", False
    except Exception:
      return "Error", False

  def tag_ticket(self, files_directory: str, ticket_id: str | int, conversation: Optional[Conversation] = None) -> Tuple[bool, str, str]:
    try:
      ticket_details = self.format_ticket_details(ticket_id)
      if not ticket_details:
        return False, "", "Could not retrieve ticket details"

      tag_conversation = Conversation(files_directory, prompt=TAG_PROMPT)
      tag_conversation.add_message(MessageRole.USER, ticket_details)

      process_queue = ProcessQueue()
      process = Process(
        agent_type="simple",
        settings=None,
        conversation=tag_conversation,
        parameters={
          "source_preference": SourcePreference.ANY,
          "model": ACTIVE_MODEL,
        }
      )
      process_id = process_queue.put(process)
      completed = process_queue.wait_for_process(process_id, timeout=TIMEOUT)
      if not completed or completed.status != ProcessStatus.COMPLETED:
        err = completed.error if completed else "Process failed or timed out"
        return False, "", f"Model error: {err}"

      if conversation is not None:
        for msg in tag_conversation.get_messages():
          conversation.add_message(msg.speaker, msg.content)
        conversation.save()

      response_msg = tag_conversation.get_latest_message()
      if response_msg and response_msg.content:
        tag, success = self.extract_tag(response_msg.content)
        tag_name = f"AI-{tag}"
        if not self.api.add_tag(ticket_id, tag_name):
          return False, "", f"Failed to add tag {tag_name}"
        if not self.api.add_tag(ticket_id, "AI-Tagged"):
          return False, tag_name, "Added tag but failed to mark as processed"
        return True, tag_name, ""
      return False, "", "No response generated by the model"
    except Exception as e:
      logger.error(f"Error processing ticket {ticket_id}: {str(e)}")
      return False, "", f"Error: {str(e)}"

  def untag_ticket(self, ticket_id: int | str) -> Tuple[int, List[str]]:
    try:
      tags = self.api.list_tags(ticket_id)
      ai_tags = [t for t in tags if isinstance(t, str) and t.startswith("AI-")]
      removed: List[str] = []
      for tag in ai_tags:
        if self.api.remove_tag(ticket_id, tag):
          removed.append(tag)
      return len(removed), removed
    except Exception as e:
      logger.error(f"Error removing AI tags from ticket {ticket_id}: {str(e)}")
      return 0, []

  def find_tickets_by_subject(self, subject: str, limit: int = 0) -> List[Dict[str, Any]]:
    all_tickets = self.api.list_tickets("open-tickets", limit=999, full_response=True) or []
    matches: List[Dict[str, Any]] = []
    for ticket in all_tickets:
      title = ticket.get('title', '')
      if isinstance(title, str) and subject.lower() in title.lower():
        matches.append({
          'id': ticket.get('id'),
          'title': title,
          'created_at': ticket.get('created_at', 'Unknown'),
          'customer': ticket.get('customer', 'Unknown'),
        })
        if limit > 0 and len(matches) >= limit:
          break
    return matches

  def process_account_ticket(self, files_directory: str, ticket_id: str | int, file: Optional[TextFile] = None, conversation: Optional[Conversation] = None) -> Tuple[bool, str, Optional[TextFile]]:
    try:
      ticket_details = self.format_ticket_details(ticket_id)
      if not ticket_details:
        return False, "Could not retrieve ticket details", None

      if file is None:
        file = TextFile(files_directory)
      current_account_list = file.get_content()

      account_conversation = Conversation(files_directory, prompt=ACCOUNT_MANAGEMENT_PROMPT)
      account_conversation.add_message(
        MessageRole.USER,
        f"Current account list:\n{current_account_list}\n\n\nNew ticket to process:\n{ticket_details}"
      )

      process_queue = ProcessQueue()
      process = Process(
        agent_type="simple",
        settings=None,
        conversation=account_conversation,
        parameters={
          "source_preference": SourcePreference.ANY,
          "model": ACTIVE_MODEL,
        }
      )
      process_id = process_queue.put(process)
      completed = process_queue.wait_for_process(process_id, timeout=TIMEOUT)
      if not completed or completed.status != ProcessStatus.COMPLETED:
        err = completed.error if completed else "Process failed or timed out"
        return False, f"Model error: {err}", None

      response = account_conversation.get_latest_message()
      if not response or not response.content:
        return False, "No response generated by the model", None

      if conversation is not None:
        for msg in account_conversation.get_messages():
          conversation.add_message(msg.speaker, msg.content)

      previous = current_account_list
      current = response.content.strip()


      # Verification step to ensure no data loss
      if previous:
        verification_conversation = Conversation(files_directory, prompt=VERIFICATION_PROMPT)
        verification_conversation.add_message(
          MessageRole.USER,
          f"Previous list:\n{previous}\n\nUpdated list:\n{current}\n\nHas any data been lost? Respond with YES or NO followed by details."
        )

        verify_process = Process(
          agent_type="simple",
          settings=None,
          conversation=verification_conversation,
          parameters={
            "source_preference": SourcePreference.ANY,
            "model": ACTIVE_MODEL,
          }
        )
        verify_process_id = process_queue.put(verify_process)
        completed_verify = process_queue.wait_for_process(verify_process_id, timeout=TIMEOUT)
        if not completed_verify or completed_verify.status != ProcessStatus.COMPLETED:
          err = completed_verify.error if completed_verify else "Verification process failed or timed out"
          return False, f"Verification error: {err}", None

        verification_msg = verification_conversation.get_latest_message()
        if not verification_msg or not verification_msg.content:
          return False, "No verification response generated", None

        if conversation is not None:
          for msg in verification_conversation.get_messages():
            conversation.add_message(msg.speaker, msg.content)

        verification_response = verification_msg.content.strip()
        if verification_response.upper().startswith("YES"):
          return False, "Data loss detected during processing", None


      file.save(content=current)
      if conversation is not None:
        conversation.save()

      return True, "", file
    except Exception as e:
      logger.error(f"Error processing account ticket {ticket_id}: {str(e)}")
      return False, f"Error: {str(e)}", None

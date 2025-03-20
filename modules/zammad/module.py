"""
Zammad integration module for Claia

This module provides functionality for interacting with the Zammad ticketing system.
"""

# External dependencies
import os
import json
import requests
import urllib.parse
import re
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Callable, TypeVar, Tuple
from tempfile import NamedTemporaryFile
from functools import wraps

# Internal dependencies
from commands.base import Command, command
from errors import Result
from settings import Settings
from conversations import Conversation
from enums import MessageRole

# Try to import AIA, but make it optional
try:
  from aia import AIASession
except ImportError:
  # Create a fallback class if AIA is not available
  class AIASession:
    def cadata_from_url(self, url):
      return ""



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                              CONSTANTS                               #
########################################################################
# Environment variable names
ENV_ZAMMAD_API_TOKEN = "TOKEN_ZAMMAD"
ENV_ZAMMAD_BASE_URL = "ZAMMAD_BASEURL"

TAG_LIST = [
  "Phishing",
  "Spam",
  "Completed",
  "NetworkHardware",
  "Jenzabar",
  "LMS",
  "Report",
  "Printers",
  "Forms",
  "Adobe",
  "InfoMaker",
  "Salesforce",
  "Classroom",
  "Login",
  "Student",
  "Filter",
  "Video",
  "AccountManagement",
  "NoCategoryFound"
]

# Predefined ticket queries
TICKET_QUERIES = {
  "new-tickets": "state_id:1",
  "open-tickets": "state_id:1 OR state_id:2 OR state_id:3",
  "reminder-tickets": "state_id:3",
  "untagged-tickets": "(state_id:1 OR state_id:2 OR state_id:3) AND !(tags:AI-Tagged)",
  "tagged-tickets": "tags:AI-Tagged",
  "high-priority": "priority.name:\"3 high\"",
  "account-management": "(tags:\"AD & User Account Management\" OR tags:AI-AccountManagement) AND (state_id:1 OR state_id:2 OR state_id:3)"
}

# Prompts
SUMMARIZE_PROMPT = f"""
You are an expert IT professional. You offer all sorts of support ranging from simple device advice to complex education software systems. You are tasked with summarizing and describing all relevant information about a provided ticket. Don't make any note on whether or not this is submitted by a student, staff, or faculty.

Some of these tickets may be requests for support, reminders from IT personel for projects, email chains between multiple various people or departments, even just normal software or computer problems. Some requests may even be unrelated or phishing/marketing emails. These tickets may also contain repeating information just like you would find in an email reply chain.

You should analyze the ticket. If there is not enough context then suggest a response that will gather more info.

Your response should follow this layout:
- First, describe all of your thoughts or observations about the ticket.
- Next, summarize the ticket, whether or not it has been completed, whether or not there are multiple facets to this tickets, wheter or not it's relevant.
- Finally suggest a potential response, even if the best response is to ignore or close the ticket. Be explicit and show your reasoning.
"""

TAG_PROMPT = f"""
You are a helpful and harmless assistant. You are Qwen developed by Alibaba. You should think step-by-step.

You are organizing tickets into categories and assigning relevant tags. Consider which category fits the ticket best. But when in doubt, use the "NoCategoryFound" tag. You never want to have inaccurate tags.

Here are the available tags. Your response MUST contain an entry from this list:
- Phishing (any emails or links that have been sent in for review, or any otherwise suspicious 3rd party emails or links)
- Spam (any marketing emails or quarantine emails)
- Completed (*this tag takes precedence for anything that fits, anything that looks completed, such as a ticket with a thank you at the end, or something that seems trivial to resolve but is very old)
- NetworkHardware (any network hardware related issues such as switches, routers, firewalls, access points, or anything that might require physical hardware installation or maintenance)
- Jenzabar (anything about the Jenzabar software)
- LMS (anything about course setup, assignment creation or grading, etc)
- Report (anything about informative reporting or reporting services)
- Printers (anything related to printers or printing, including drivers or driver installs, toners need changing, etc)
- Forms (a webform needs updating, the emails are going to the wrong recipient, new form needed, etc)
- Adobe (anything requested about the Adobe software or licenses)
- InfoMaker (anything requested about the InfoMake software or related processes)
- Salesforce (anything requested about the Salesforce platform or related issues)
- Classroom (anything related to classroom troubles, teacher's computer not turning on, smartboard not working, projector is dim, etc)
- Login (locked out of account, needs password reset, can't find username or password, MFA trouble, etc)
- Student (any student submitted request that doesn't fit the other categories, these would likely be simple issues, this could be trouble with an office license, library access issues, laptop is having trouble, etc)
- Filter (the website filter, wifi is blocking a device's access)
- Video (any video uploads or class videos if requested by a faculty or staff member. This includes Zoom, YouTube, Teams Meetings, and misc recordings)
- AccountManagement (misc account management issues, such as disabling or adding permissions, updating account names, etc)
- NoCategoryFound (use this if no other category seems related or is just not a good fit)

Assign a tag using the following format:
[TAG]tag_name[/TAG]

Example 1:
[TAG]Phishing[/TAG]

Example 2:
[TAG]NoCategoryFound[/TAG]

Notes:
- You MUST use the above tags.
- You MUST use the tag name exactly as it is listed above.
- You MUST use the [TAG] and [/TAG] format.
- The tag MUST start with [TAG] and end with [/TAG].

Respond to the user's request by assigning the appropriate tag. The answer MUST be one of the above tags.
"""

ACCOUNT_MANAGEMENT_PROMPT = f"""
You are an expert IT professional specializing in account management. Your task is to analyze a ticket and extract information about accounts that need work.

The ticket is related to account management. Review the ticket details and identify:
1. The account(s) that need work
2. What type of work needs to be done (creation, modification, deletion, permission changes, etc.)
3. Any specific details about the work required

Based on the ticket information, update the current list of accounts that need work. The list should be in a structured format with each entry containing:
- Account name/identifier
- Type of work needed
- Specific details
- Source ticket ID

Your response should ONLY contain the updated list in a clear, structured format. Do not include any explanations or additional text.
"""

VERIFICATION_PROMPT = f"""
You are an expert data auditor. Your task is to compare two versions of a list and verify that no important data has been lost.
The updated list should contain all the relevant information from the previous list, plus any new additions.
If you find that data has been lost, clearly identify what's missing. If everything looks good, confirm that all data has been preserved.
"""



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


def get_settings() -> ZammadSettings:
  """
  Get the Zammad settings.

  Returns:
    ZammadSettings: The Zammad settings.
  """
  return ZammadSettings()



########################################################################
#                              DECORATORS                              #
########################################################################
# Type variable for generic function return type
T = TypeVar('T')

def require_zammad_config(func: Callable[..., T]) -> Callable[..., T]:
  """
  Decorator to check if Zammad is properly configured before executing a command.

  Args:
    func: The function to decorate

  Returns:
    The decorated function that checks for Zammad configuration
  """
  @wraps(func)
  def wrapper(self, settings: Settings, *args, **kwargs) -> T:
    # Get Zammad settings
    zammad_settings = get_settings()

    # Check if Zammad is configured
    if not zammad_settings.is_configured():
      return f"Zammad is not properly configured. Please set {ENV_ZAMMAD_API_TOKEN} and {ENV_ZAMMAD_BASE_URL} environment variables."

    # Create Zammad API client and pass it to the function
    zammad = ZammadAPI(zammad_settings.base_url, zammad_settings.api_token)

    # Call the original function with the API client
    return func(self, settings, zammad, *args, **kwargs)

  return wrapper



########################################################################
#                              API CLASS                               #
########################################################################
class ZammadAPI:
  """Class for interacting with the Zammad API."""
  def __init__(self, base_url: str, api_token: str) -> None:
    self.base_url = base_url
    self.api_token = api_token
    self.headers = {
      "Authorization": f"Token token={self.api_token}",
      "Content-Type": "application/json"
    }
    self.session = AIASession()

  def _make_request(self, method: str, endpoint: str, data=None):
    """Make a request to the Zammad API with proper certificate handling."""
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
        print(f"API request error ({method} {endpoint}): {str(e)}")
        raise

  def get(self, endpoint: str):
    """Make a GET request to the Zammad API."""
    return self._make_request('get', endpoint)

  def post(self, endpoint: str, data: dict):
    """Make a POST request to the Zammad API."""
    return self._make_request('post', endpoint, data)

  def delete(self, endpoint: str, data: dict):
    """Make a DELETE request to the Zammad API."""
    return self._make_request('delete', endpoint, data)

  def add_tag(self, ticket_id: int, tag: str) -> bool:
    """
    Add a tag to a ticket.

    Args:
      ticket_id: The ID of the ticket
      tag: The tag to add

    Returns:
      bool: True if successful, False otherwise
    """
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      self.post("tags/add", data)
      print(f"Successfully added tag '{tag}' to ticket {ticket_id}")
      return True
    except Exception as e:
      print(f"Error adding tag '{tag}' to ticket {ticket_id}: {str(e)}")
      return False

  def list_tickets(self, query_name: str = "open-tickets", limit: int = 100, full_response: bool = True):
    """
    List tickets based on a predefined query or custom query string.

    Args:
      query_name: Name of predefined query or custom query string
      limit: Maximum number of tickets per page
      full_response: Whether to fetch all pages or just the first page

    Returns:
      List of ticket IDs or None if an error occurred
    """
    # Get the query string from predefined queries or use the input as a custom query
    query = TICKET_QUERIES.get(query_name, query_name)
    encoded_query = urllib.parse.quote(query)

    try:
      # Get the first page of results
      page = 1
      response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
      tickets = response["tickets"]
      ticket_count = response["tickets_count"]
      print(f"tickets: {ticket_count}")

      # If full_response is True, fetch all pages
      while full_response and response["tickets_count"] > 0:
        print(f"total tickets: {ticket_count}")
        page += 1
        response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
        tickets.extend(response["tickets"])
        ticket_count += response["tickets_count"]

      return tickets
    except Exception as e:
      print(f"Error listing tickets: {str(e)}")
      return None

  def _clean_html_content(self, text: str) -> str:
    """Clean HTML content from ticket articles."""
    if not text:
      return ""

    # First use BeautifulSoup to handle HTML properly
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text(separator='\n')

    # Remove extra whitespace and normalize newlines
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text.strip())

    return clean_text

  def _extract_unique_content(self, articles: List[dict]) -> List[dict]:
    """Extract unique content from ticket articles to avoid duplication."""
    seen_content = set()
    unique_articles = []

    for article in articles:
      # Clean the body content
      clean_body = self._clean_html_content(article['body'])

      # Split into paragraphs and process each
      paragraphs = clean_body.split('\n\n')
      unique_paragraphs = []

      for para in paragraphs:
        # Normalize the paragraph to help with matching
        normalized_para = re.sub(r'\s+', ' ', para.strip())
        if len(normalized_para) > 30:  # Only check substantial paragraphs
          if normalized_para not in seen_content:
            seen_content.add(normalized_para)
            unique_paragraphs.append(para)

      if unique_paragraphs:
        # Create a new article with only unique content
        new_article = article.copy()
        new_article['body'] = '\n\n'.join(unique_paragraphs)
        unique_articles.append(new_article)

    return unique_articles

  def get_ticket_details(self, ticket_id: str) -> str:
    """
    Get detailed information about a ticket.

    Args:
      ticket_id: The ID of the ticket

    Returns:
      str: Formatted ticket details
    """
    try:
      # Get ticket and article data
      ticket = self.get(f"tickets/{ticket_id}")
      articles = self.get(f"ticket_articles/by_ticket/{ticket_id}")

      # Process articles to remove duplicates
      unique_articles = self._extract_unique_content(articles)

      # Format the response
      response = []
      response.append("Ticket Details:")
      response.append(f"Ticket ID: {ticket['id']}")
      response.append(f"Number: {ticket['number']}")
      response.append(f"Title: {ticket['title']}")
      response.append(f"State: {ticket['state_id']}")
      response.append(f"Priority: {ticket['priority_id']}")
      response.append(f"Created At: {ticket['created_at']}")
      response.append(f"Updated At: {ticket['updated_at']}")
      response.append("")
      response.append("Articles:")

      for article in unique_articles:
        response.append(f"Article ID: {article['id']}")
        response.append(f"From: {article['from']}")
        response.append(f"To: {article['to']}")
        response.append(f"CC: {article['cc']}")
        response.append(f"Subject: {article['subject']}")
        response.append(f"Created At: {article['created_at']}")
        response.append(f"Updated At: {article['updated_at']}")
        response.append(f"Body:\n{article['body']}")
        response.append("-" * 50)

      return "\n".join(response)
    except Exception as e:
      return f"Error getting ticket details: {str(e)}"

  def list_tags(self, ticket_id: int) -> list:
    """
    List all tags for a specific ticket.

    Args:
      ticket_id: The ID of the ticket

    Returns:
      list: List of tags
    """
    try:
      response = self.get(f"tags?object=Ticket&o_id={ticket_id}")
      return response.get("tags", [])
    except Exception as e:
      print(f"Error listing tags for ticket {ticket_id}: {str(e)}")
      return []

  def remove_tag(self, ticket_id: int, tag: str) -> bool:
    """
    Remove a specific tag from a ticket.

    Args:
      ticket_id: The ID of the ticket
      tag: The tag to remove

    Returns:
      bool: True if successful, False otherwise
    """
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      self.delete("tags/remove", data)
      print(f"Successfully removed tag '{tag}' from ticket {ticket_id}")
      return True
    except Exception as e:
      print(f"Error removing tag '{tag}' from ticket {ticket_id}: {str(e)}")
      return False



########################################################################
#                            COMMAND CLASS                             #
########################################################################
class ModuleCommands(Command):
  """Command class for Zammad ticket management"""

  @command(
    path=["list"],
    description="List tickets from Zammad",
    help_text="List tickets from Zammad based on a query",
    parameters={
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Query name or custom query string (default: open-tickets)",
          "default": "open-tickets"
        }
      }
    },
    returns={
      "type": "string",
      "description": "List of tickets"
    },
    ai_callable=True
  )
  @require_zammad_config
  def list_tickets(self, settings: Settings, zammad: ZammadAPI, query: str = "open-tickets") -> str:
    """
    List tickets from Zammad based on a query.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      query: Query name or custom query string

    Returns:
      str: List of tickets
    """
    # Get tickets
    tickets = zammad.list_tickets(query)

    # Format the response
    if not tickets:
      return "No tickets found."

    response = f"Found {len(tickets)} tickets:\n\n"
    for ticket_id in tickets:
      response += f"- Ticket ID: {ticket_id}\n"

    return response

  @command(
    path=["details"],
    description="Get details for a Zammad ticket",
    help_text="Get details for a Zammad ticket using its ID",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket to retrieve"
        }
      },
      "required": ["ticket_id"]
    },
    returns={
      "type": "string",
      "description": "Ticket details"
    },
    ai_callable=True
  )
  @require_zammad_config
  def get_ticket_details(self, settings: Settings, zammad: ZammadAPI, ticket_id: str) -> str:
    """
    Get details of a specific ticket from Zammad.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to retrieve

    Returns:
      str: Ticket details
    """
    return zammad.get_ticket_details(ticket_id)

  @command(
    path=["tag", "add"],
    description="Add a tag to a Zammad ticket",
    help_text="Add a tag to a Zammad ticket",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket to tag"
        },
        "tag": {
          "type": "string",
          "description": "The tag to add to the ticket"
        }
      },
      "required": ["ticket_id", "tag"]
    },
    returns={
      "type": "string",
      "description": "Result message"
    },
    ai_callable=True
  )
  @require_zammad_config
  def add_tag(self, settings: Settings, zammad: ZammadAPI, ticket_id: str, tag: str) -> str:
    """
    Add a tag to a ticket in Zammad.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket to tag
      tag: The tag to add to the ticket

    Returns:
      str: Result message
    """
    result = zammad.add_tag(ticket_id, tag)

    if result:
      return f"Successfully added tag '{tag}' to ticket {ticket_id}."
    else:
      return f"Failed to add tag '{tag}' to ticket {ticket_id}."

  @command(
    path=["tag", "remove"],
    description="Remove a tag from a Zammad ticket",
    help_text="Remove a tag from a Zammad ticket",
    parameters={
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "The ID of the ticket"
        },
        "tag": {
          "type": "string",
          "description": "The tag to remove from the ticket"
        }
      },
      "required": ["ticket_id", "tag"]
    },
    returns={
      "type": "string",
      "description": "Result message"
    },
    ai_callable=True
  )
  @require_zammad_config
  def remove_tag(self, settings: Settings, zammad: ZammadAPI, ticket_id: str, tag: str) -> str:
    """
    Remove a tag from a ticket in Zammad.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      ticket_id: The ID of the ticket
      tag: The tag to remove from the ticket

    Returns:
      str: Result message
    """
    result = zammad.remove_tag(ticket_id, tag)

    if result:
      return f"Successfully removed tag '{tag}' from ticket {ticket_id}."
    else:
      return f"Failed to remove tag '{tag}' from ticket {ticket_id}."

  @command(
    path=["process"],
    description="Process untagged tickets",
    help_text="Process untagged tickets and add AI tags",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def process_tickets(self, settings: Settings, zammad: ZammadAPI) -> str:
    """
    Process untagged tickets and add AI tags.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance

    Returns:
      str: Processing result
    """
    # Process tickets
    result = zammad_run_process(settings, zammad)
    return "Ticket processing completed."

  @command(
    path=["untag"],
    description="Remove AI tags from tickets",
    help_text="Remove AI tags from all tagged tickets",
    parameters={
      "type": "object",
      "properties": {}
    },
    returns={
      "type": "string",
      "description": "Untagging result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def untag_tickets(self, settings: Settings, zammad: ZammadAPI) -> str:
    """
    Remove AI tags from all tagged tickets.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance

    Returns:
      str: Untagging result
    """
    # Get tagged tickets
    tickets = zammad.list_tickets("tagged-tickets")

    if not tickets:
      return "No tagged tickets found"

    removed_count = 0

    # Remove AI tags from each ticket
    for ticket_id in tickets:
      tags = zammad.list_tags(ticket_id)
      ai_tags = [tag for tag in tags if tag.startswith("AI-")]

      if ai_tags:
        for tag in ai_tags:
          if zammad.remove_tag(ticket_id, tag):
            removed_count += 1

    return f"Completed! Removed {removed_count} AI tags from {len(tickets)} tickets"

  @command(
    path=["account-management"],
    description="Process account management tickets",
    help_text="Process tickets with account management tags and build a list of accounts that need work",
    parameters={
      "type": "object",
      "properties": {
        "output_file": {
          "type": "string",
          "description": "File to save the account list to (default: account_list.txt)",
          "default": "account_list.txt"
        },
        "limit": {
          "type": "integer",
          "description": "Maximum number of tickets to process (default: 50)",
          "default": 50
        }
      }
    },
    returns={
      "type": "string",
      "description": "Processing result"
    },
    ai_callable=True
  )
  @require_zammad_config
  def process_account_tickets(self, settings: Settings, zammad: ZammadAPI, output_file: str = "account_list.txt", limit: int = 50) -> str:
    """
    Process tickets with account management tags and build a list of accounts that need work.

    Args:
      settings: Application settings
      zammad: ZammadAPI instance
      output_file: File to save the account list to
      limit: Maximum number of tickets to process

    Returns:
      str: Processing result
    """
    # Import here to avoid circular imports
    from models import run as model_run
    from conversations.files import FileFactory, TextFile

    # Get tickets matching the account management query
    tickets = zammad.list_tickets("account-management", limit=limit)

    if not tickets:
      return "No account management tickets found."

    # Create or load a conversation
    conversation = Conversation(
      base_directory=settings.conversation_directory,
      files_directory=settings.conversation_files_directory,
      title="Account Management Processing"
    )

    # Display initial status
    print(f"\n{'='*50}")
    print(f"Starting to process {len(tickets)} account management tickets")
    print(f"{'='*50}\n")

    # Initialize or load the account list file
    file_id = None
    current_account_list = ""

    if os.path.exists(output_file):
      print(f"Loading existing account list from {output_file}")
      file_id = conversation.add_file(output_file)
      account_file = conversation.get_file(file_id)
      if account_file and isinstance(account_file, TextFile):
        current_account_list = account_file.get_preview()
    else:
      print(f"Creating new account list file: {output_file}")
      # Create an empty file
      with open(output_file, "w") as f:
        f.write("")
      file_id = conversation.add_file(output_file)

    # Process each ticket
    processed_count = 0
    successful_count = 0
    remaining_tickets = tickets.copy()
    retry_count = {}  # Track how many times each ticket has been retried

    while remaining_tickets:
      # Get the next ticket
      ticket_id = remaining_tickets.pop(0)

      # Track retry attempts
      if ticket_id not in retry_count:
        retry_count[ticket_id] = 0

      # Limit maximum retries per ticket to prevent infinite loops
      max_retries = 3
      if retry_count[ticket_id] >= max_retries:
        print(f"⚠️ Ticket {ticket_id} exceeded maximum retry attempts ({max_retries}). Skipping.")
        continue

      retry_count[ticket_id] += 1

      # Display attempt information
      attempt_info = f" (Retry #{retry_count[ticket_id]})" if retry_count[ticket_id] > 1 else ""
      print(f"\n{'-'*50}")
      print(f"Processing ticket ID: {ticket_id}{attempt_info} ({processed_count+1}/{len(tickets)})")

      # Get ticket details
      ticket_details = zammad.get_ticket_details(ticket_id)

      # Prepare optimized messages for the LLM
      # For retry attempts, use a stronger prompt about preserving data
      is_retry = retry_count[ticket_id] > 1
      retry_instruction = "\n\nIMPORTANT: Previous processing of this ticket resulted in data loss. Make sure to preserve ALL existing information while adding new data from this ticket." if is_retry else ""

      account_messages = [
        {"role": "system", "content": ACCOUNT_MANAGEMENT_PROMPT + retry_instruction},
        {"role": "user", "content": f"Current account list:\n{current_account_list}\n\n\nNew ticket to process:\n{ticket_details}"}
      ]

      # Run the AI model to update the account list
      print(f"Sending ticket to LLM for processing...")
      result = model_run(settings.active_model, account_messages, settings=settings)

      if result.is_error():
        print(f"❌ Error processing ticket {ticket_id}: {result.get_message()}")
        # Add ticket back to the end of the queue for retry
        if retry_count[ticket_id] < max_retries:
          remaining_tickets.append(ticket_id)
          print(f"Added ticket {ticket_id} back to queue for retry later")
        continue

      # Update account list with model's response
      if result.data:
        print("✓ Successfully processed ticket")
        previous_account_list = current_account_list
        current_account_list = result.data.strip()

        # Verify no data has been lost in the update
        if previous_account_list:
          print("Verifying that no data has been lost...")
          verification_messages = [
            {"role": "system", "content": VERIFICATION_PROMPT},
            {"role": "user", "content": f"Previous list:\n{previous_account_list}\n\nUpdated list:\n{current_account_list}\n\nHas any data been lost? Respond with YES or NO followed by details."}
          ]

          verification_result = model_run(settings.active_model, verification_messages, settings=settings)

          if verification_result.is_error():
            print(f"⚠️ Error during verification: {verification_result.get_message()}")
            # Add ticket back to the end of the queue for retry
            if retry_count[ticket_id] < max_retries:
              remaining_tickets.append(ticket_id)
              print(f"Added ticket {ticket_id} back to queue for retry later (verification error)")
            continue

          verification_response = verification_result.data.strip()
          if verification_response.startswith("YES"):
            print("⚠️ WARNING: Possible data loss detected!")
            print(f"Details: {verification_response}")
            print("Reverting to previous account list...")
            current_account_list = previous_account_list

            # Add ticket back to the end of the queue for retry
            if retry_count[ticket_id] < max_retries:
              remaining_tickets.append(ticket_id)
              print(f"Added ticket {ticket_id} back to queue for retry later (data loss detected)")
            continue
          else:
            print("✅ Verification passed: No data has been lost")
            # Ticket processed successfully

        # Get the file object and update its content
        account_file = conversation.get_file(file_id)
        if account_file and isinstance(account_file, TextFile):
          # Save the updated content using BaseFile methods
          with open(output_file, "w") as f:
            f.write(current_account_list)

          # Update the file in the conversation
          file_id = conversation.add_file(output_file)

          # Add a message to the conversation about the update
          conversation.add_message(
            role=MessageRole.SYSTEM,
            content=f"Updated account list after processing ticket {ticket_id}"
          )

          successful_count += 1

      processed_count += 1

      # Print status information
      print(f"Processed ticket: {ticket_id}")
      print(f"Remaining tickets: {len(remaining_tickets)}")
      print(f"Current list size: {len(current_account_list)} characters")
      print(f"{'-'*50}\n")

      # Save the conversation state
      conversation.save()

    print(f"\n{'='*50}")
    print(f"Processing complete! Successfully processed {successful_count}/{len(tickets)} tickets.")
    print(f"Account list saved to {output_file}")
    print(f"{'='*50}\n")

    return f"Processed {successful_count} tickets. Account list saved to {output_file}"



########################################################################
#                              FUNCTIONS                               #
########################################################################
def extract_tag_from_response(response: str) -> Tuple[str, bool]:
  """
  Extract tag from AI model response.

  Args:
    response: The AI model response text

  Returns:
    Tuple containing the extracted tag and a success flag
  """
  if not response:
    return "Blank", False

  # Remove any escape characters
  cleaned_response = response.replace("\\", "")

  try:
    # Extract tag from [TAG]tag[/TAG] format
    if "[TAG]" in cleaned_response and "[/TAG]" in cleaned_response:
      start = cleaned_response.index("[TAG]") + len("[TAG]")
      end = cleaned_response.index("[/TAG]")
      tag = cleaned_response[start:end].strip()

      # Validate tag is in our list
      if tag in TAG_LIST:
        return tag, True
      else:
        return "Unknown", False
    else:
      return "Blank", False
  except Exception as e:
    print(f"Error extracting tag: {e}")
    return "Error", False

def zammad_run_process(settings: Settings, zammad: ZammadAPI) -> Result:
  """
  Process untagged tickets and add AI tags.

  Args:
    settings: Application settings
    zammad: ZammadAPI instance

  Returns:
    Result object
  """
  # Import here to avoid circular imports
  from models import run as model_run

  result = Result()
  tickets = zammad.list_tickets("untagged-tickets")

  # For testing, limit to a subset of tickets
  temp_tickets = tickets[11:] if len(tickets) > 11 else tickets

  processed_count = 0
  for ticket_id in temp_tickets:
    # Get ticket details
    ticket_details = zammad.get_ticket_details(ticket_id)

    # Prepare messages for the AI model
    tagging_messages = [
      {"role": "system", "content": TAG_PROMPT},
      {"role": "user", "content": ticket_details}
    ]

    print("-" * 50)
    print(f"Processing ticket ID: {ticket_id}")

    # Run the AI model to get tag
    tagging_result = model_run(settings.active_model, tagging_messages, settings=settings)

    if tagging_result.is_error():
      print(f"Error running tagging model: {tagging_result.get_message()}")
      continue

    print(f"Tagging Result:\n{tagging_result.data}")
    print("-" * 50)

    # Extract and apply tag
    if tagging_result.data:
      tag, success = extract_tag_from_response(tagging_result.data)

      # Add the appropriate tag
      if success:
        zammad.add_tag(ticket_id, f"AI-{tag}")
      else:
        zammad.add_tag(ticket_id, f"AI-{tag}")

      # Mark as processed
      zammad.add_tag(ticket_id, "AI-Tagged")
      processed_count += 1

  result.data = f"Processed {processed_count} tickets"
  return result
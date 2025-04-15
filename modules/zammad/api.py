"""
Zammad API client for Claia.

This module provides the API client for interacting with the Zammad ticketing system.
"""

# External dependencies
import logging
import requests
import urllib.parse
import re
import json
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple
from tempfile import NamedTemporaryFile

# Try to import AIA, but make it optional
try:
  from aia import AIASession
except ImportError:
  # Create a fallback class if AIA is not available
  class AIASession:
    def cadata_from_url(self, url):
      return ""

# Internal dependencies
from .constants import TICKET_QUERIES



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               API CLASS                              #
########################################################################
class ZammadAPI:
  """Class for interacting with the Zammad API."""
  def __init__(self, base_url: str, api_token: str) -> None:
    logger.debug("Initializing ZammadAPI with base_url: %s", base_url)
    self.base_url = base_url
    self.api_token = api_token
    self.headers = {
      "Authorization": f"Token token={self.api_token}",
      "Content-Type": "application/json"
    }
    self.session = AIASession()
    logger.debug("ZammadAPI initialization complete")

  def _make_request(self, method: str, endpoint: str, data=None):
    """Make a request to the Zammad API with proper certificate handling."""
    url = f"{self.base_url}{endpoint}"
    logger.debug("Making %s request to endpoint: %s", method, endpoint)
    cadata = self.session.cadata_from_url(url)

    with NamedTemporaryFile("w") as pem_file:
      pem_file.write(cadata)
      pem_file.flush()
      logger.debug("Created temporary PEM file for certificate")

      try:
        if method.lower() == 'get':
          logger.debug("Sending GET request")
          response = requests.get(url, headers=self.headers, verify=pem_file.name)
        elif method.lower() == 'post':
          logger.debug("Sending POST request with data: %s", data)
          response = requests.post(url, headers=self.headers, json=data, verify=pem_file.name)
        elif method.lower() == 'delete':
          logger.debug("Sending DELETE request with data: %s", data)
          response = requests.delete(url, headers=self.headers, json=data, verify=pem_file.name)
        else:
          logger.error("Unsupported HTTP method: %s", method)
          raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        logger.debug("Request successful with status code: %d", response.status_code)
        return response.json() if response.content else None
      except Exception as e:
        logger.error("API request error (%s %s): %s", method, endpoint, str(e))
        raise

  def get(self, endpoint: str):
    """Make a GET request to the Zammad API."""
    logger.debug("Making GET request to endpoint: %s", endpoint)
    return self._make_request('get', endpoint)

  def post(self, endpoint: str, data: dict):
    """Make a POST request to the Zammad API."""
    logger.debug("Making POST request to endpoint: %s with data: %s", endpoint, data)
    return self._make_request('post', endpoint, data)

  def delete(self, endpoint: str, data: dict):
    """Make a DELETE request to the Zammad API."""
    logger.debug("Making DELETE request to endpoint: %s with data: %s", endpoint, data)
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
    logger.debug("Adding tag '%s' to ticket %d", tag, ticket_id)
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      self.post("tags/add", data)
      logger.info("Successfully added tag '%s' to ticket %d", tag, ticket_id)
      return True
    except Exception as e:
      logger.error("Error adding tag '%s' to ticket %d: %s", tag, ticket_id, str(e))
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

    logger.debug("Listing tickets with query: %s, limit: %d, full_response: %s", query_name, limit, full_response)
    # Get the query string from predefined queries or use the input as a custom query
    query = TICKET_QUERIES.get(query_name, query_name)
    encoded_query = urllib.parse.quote(query)
    logger.debug("Using encoded query: %s", encoded_query)

    try:
      # Get the first page of results
      page = 1
      response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
      tickets = response["tickets"]
      ticket_count = response["tickets_count"]
      logger.debug("Initial page retrieved with %d tickets", ticket_count)

      # If full_response is True, fetch all pages
      while full_response and response["tickets_count"] > 0:
        logger.debug("Fetching page %d, total tickets so far: %d", page + 1, ticket_count)
        page += 1
        response = self.get(f"tickets/search?query={encoded_query}&page={page}&per_page={limit}&sort_by=updated_at&order_by=asc")
        tickets.extend(response["tickets"])
        ticket_count += response["tickets_count"]

      logger.info("Retrieved total of %d tickets", len(tickets))
      return tickets
    except Exception as e:
      logger.error("Error listing tickets: %s", str(e))
      return None

  def _clean_html_content(self, text: str) -> str:
    """Clean HTML content from ticket articles."""
    logger.debug("Cleaning HTML content of length: %d", len(text) if text else 0)
    if not text:
      return ""

    # First use BeautifulSoup to handle HTML properly
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text(separator='\n')

    # Remove extra whitespace and normalize newlines
    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text.strip())
    logger.debug("Cleaned text length: %d", len(clean_text))

    return clean_text

  def _extract_unique_content(self, articles: List[dict]) -> List[dict]:
    """Extract unique content from ticket articles to avoid duplication."""
    logger.debug("Extracting unique content from %d articles", len(articles))
    seen_content = set()
    unique_articles = []

    for article in articles:
      # Clean the body content
      clean_body = self._clean_html_content(article['body'])

      # Split into paragraphs and process each
      paragraphs = clean_body.split('\n\n')
      unique_paragraphs = []
      logger.debug("Processing %d paragraphs from article %s", len(paragraphs), article.get('id', 'unknown'))

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

    logger.debug("Extracted %d unique articles from %d original articles", len(unique_articles), len(articles))
    return unique_articles

  def get_ticket_details(self, ticket_id: str) -> str:
    """
    Get detailed information about a ticket.

    Args:
      ticket_id: The ID of the ticket

    Returns:
      str: Formatted ticket details
    """
    logger.debug("Getting details for ticket ID: %s", ticket_id)
    try:
      # Get ticket and article data
      ticket = self.get(f"tickets/{ticket_id}")
      articles = self.get(f"ticket_articles/by_ticket/{ticket_id}")
      logger.debug("Retrieved ticket data and %d articles", len(articles))

      # Process articles to remove duplicates
      unique_articles = self._extract_unique_content(articles)
      logger.debug("Processed %d unique articles", len(unique_articles))

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

      logger.debug("Successfully formatted ticket details")
      return "\n".join(response)
    except Exception as e:
      logger.error("Error getting ticket details: %s", str(e))
      return f"Error getting ticket details: {str(e)}"

  def list_tags(self, ticket_id: int) -> list:
    """
    List all tags for a specific ticket.

    Args:
      ticket_id: The ID of the ticket

    Returns:
      list: List of tags
    """
    logger.debug("Listing tags for ticket ID: %d", ticket_id)
    try:
      response = self.get(f"tags?object=Ticket&o_id={ticket_id}")
      tags = response.get("tags", [])
      logger.debug("Retrieved %d tags for ticket %d", len(tags), ticket_id)
      return tags
    except Exception as e:
      logger.error("Error listing tags for ticket %d: %s", ticket_id, str(e))
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
    logger.debug("Removing tag '%s' from ticket %d", tag, ticket_id)
    data = {
      "item": tag,
      "object": "Ticket",
      "o_id": ticket_id
    }

    try:
      self.delete("tags/remove", data)
      logger.info("Successfully removed tag '%s' from ticket %d", tag, ticket_id)
      return True
    except Exception as e:
      logger.error("Error removing tag '%s' from ticket %d: %s", tag, ticket_id, str(e))
      return False

  def delete_ticket(self, ticket_id: int) -> bool:
    """
    Delete a specific ticket from Zammad.

    Args:
      ticket_id: The ID of the ticket to delete

    Returns:
      bool: True if successful, False otherwise
    """
    logger.debug("Deleting ticket with ID: %d", ticket_id)
    try:
      self.delete(f"tickets/{ticket_id}", {})
      logger.info("Successfully deleted ticket with ID: %d", ticket_id)
      return True
    except Exception as e:
      logger.error("Error deleting ticket with ID %d: %s", ticket_id, str(e))
      return False
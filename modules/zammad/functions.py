# External dependencies
import json
from typing import Dict, Any, List, Optional

# Module dependencies
from modules.zammad.api import ZammadAPI
from modules.zammad.settings import get_settings



##################################################
#                FUNCTION DEFINITIONS            #
##################################################
# Define the functions that can be called by the AI
FUNCTION_DEFINITIONS = [
  {
    "name": "list_tickets",
    "description": "Get a list of tickets IDs from Zammad",
    "parameters": {
      "type": "object",
      "properties": {}
    },
    "returns": {
      "type": "string",
      "description": "A list of ticket IDs"
    }
  },
  {
    "name": "get_ticket_details",
    "description": "Get details for a Zammad ticket using its ID",
    "parameters": {
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "the ticket id"
        }
      },
      "required": ["id"]
    },
    "returns": {
      "type": "string",
      "description": "the ticket details and articles in a human readable format"
    }
  },
  {
    "name": "add_tag_to_ticket",
    "description": "Add a categorization tag to a given ticket in Zammad, the tag must come from an approved list of tags",
    "parameters": {
      "type": "object",
      "properties": {
        "ticket_id": {
          "type": "string",
          "description": "the ticket id"
        },
        "tag": {
          "type": "string",
          "description": "the name of the tag"
        }
      },
      "required": ["ticket_id"]
    },
    "returns": {
      "type": "string",
      "description": "the ticket details and articles in a human readable format"
    }
  }
]



##################################################
#                   FUNCTIONS                    #
##################################################
def get_ticket_details(ticket_id: str) -> str:
  """
  Get details of a specific ticket from Zammad.
  
  Args:
    ticket_id: The ID of the ticket to retrieve
    
  Returns:
    str: The ticket details as a formatted string
  """
  settings = get_settings()
  
  if not settings.is_configured():
    return "Zammad is not properly configured. Please set ZAMMAD_API_TOKEN and ZAMMAD_BASE_URL environment variables."
  
  # Create Zammad API client
  zammad = ZammadAPI(settings.base_url, settings.api_token)
  
  # Get ticket details
  return zammad.get_ticket_details(ticket_id)

def list_tickets(query_name: str = "open-tickets") -> str:
  """
  List tickets from Zammad based on a query.
  
  Args:
    query_name: The name of the predefined query or a custom query string
    
  Returns:
    str: The list of tickets as a formatted string
  """
  settings = get_settings()
  
  if not settings.is_configured():
    return "Zammad is not properly configured. Please set ZAMMAD_API_TOKEN and ZAMMAD_BASE_URL environment variables."
  
  # Create Zammad API client
  zammad = ZammadAPI(settings.base_url, settings.api_token)
  
  # Get tickets
  tickets = zammad.list_tickets(query_name)
  
  # Format the response
  if not tickets:
    return "No tickets found."
    
  response = f"Found {len(tickets)} tickets:\n\n"
  for ticket_id in tickets:
    response += f"- Ticket ID: {ticket_id}\n"
    
  return response

def add_tag(ticket_id: str, tag: str) -> str:
  """
  Add a tag to a ticket in Zammad.
  
  Args:
    ticket_id: The ID of the ticket to tag
    tag: The tag to add to the ticket
    
  Returns:
    str: A message indicating success or failure
  """
  settings = get_settings()
  
  if not settings.is_configured():
    return "Zammad is not properly configured. Please set ZAMMAD_API_TOKEN and ZAMMAD_BASE_URL environment variables."
  
  # Create Zammad API client
  zammad = ZammadAPI(settings.base_url, settings.api_token)
  
  # Add tag to ticket
  result = zammad.add_tag(ticket_id, tag)
  
  if result:
    return f"Successfully added tag '{tag}' to ticket {ticket_id}."
  else:
    return f"Failed to add tag '{tag}' to ticket {ticket_id}." 
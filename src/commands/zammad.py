# Internal dependencies
import help

from commands.base import Command
from errors import Result
from settings import Settings

# External dependencies
import requests
import json
import urllib.parse

from aia import AIASession
from tempfile import NamedTemporaryFile



##################################################
#                 COMMAND CLASS                  #
##################################################
class ZammadCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    if len(commands) > 1:
      if commands[1] == "list" or commands[1] == "query":
        if len(commands) > 2:
          listTickets(settings, commands[2])
        else:
          listTickets(settings)
      elif commands[1] == "details" and len(commands) > 2:
        getTicketDetails(settings, commands[2])
      elif commands[1] == "test" and len(commands) > 2:
        print(invoke_zammad_api(settings, commands[2]))
      else:
        help.unrecognizedCommand()
    else:
      help.zammadCommands()

    return result



##################################################
#                   FUNCTIONS                    #
##################################################
def invoke_zammad_api(settings: Settings, endpoint: str) -> dict:
  headers = {
    "Authorization": f"Token token={settings.zammad_api_token}",
    "Content-Type": "application/json"
  }

  url = f"{settings.zammad_base_url}{endpoint}"
  session = AIASession()
  cadata = session.cadata_from_url(url)
  with NamedTemporaryFile("w") as pem_file:
    pem_file.write(cadata)
    pem_file.flush()
    response = requests.get(url, headers=headers, verify=pem_file.name)

  response.raise_for_status()
  return response.json()

def listTickets(settings: Settings, query_name: str = "open-tickets") -> None:
  queries = {
    "open-tickets": "state_id:1",
  }

  if query_name in queries:
    query = queries[query_name]
  else:
    query = query_name

  encoded_query = urllib.parse.quote(query)
  endpoint = f"tickets/search?query={encoded_query}&limit=10"

  try:
    result = invoke_zammad_api(settings, endpoint)
    print(f"Tickets matching query '{query_name}':")
    for ticket_id in result['tickets']:
      print(f"- Ticket ID: {ticket_id}")
  except Exception as e:
    print(f"Error listing tickets: {str(e)}")

def getTicketDetails(settings: Settings, ticket_id: str) -> None:
  try:
    ticket = invoke_zammad_api(settings, f"tickets/{ticket_id}")
    articles = invoke_zammad_api(settings, f"ticket_articles/by_ticket/{ticket_id}")

    print("Ticket Details:")
    print(f"Ticket ID: {ticket['id']}")
    print(f"Number: {ticket['number']}")
    print(f"Title: {ticket['title']}")
    print(f"State: {ticket['state_id']}")
    print(f"Priority: {ticket['priority_id']}")
    print(f"Created At: {ticket['created_at']}")
    print(f"Updated At: {ticket['updated_at']}")

    print("\nArticles:")
    for article in articles:
      print(f"\nArticle ID: {article['id']}")
      print(f"From: {article['from']}")
      print(f"To: {article['to']}")
      print(f"CC: {article['cc']}")
      print(f"Subject: {article['subject']}")
      print(f"Created At: {article['created_at']}")
      print(f"Updated At: {article['updated_at']}")
      print(f"Body:\n{article['body']}")
      print("-" * 50)

  except Exception as e:
    print(f"Error getting ticket details: {str(e)}")

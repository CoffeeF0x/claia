# Internal dependencies
import help

from commands.base import Command
from functions.zammad import ZammadAPI
from models.registry import run as model_run
from functions.definitions import zammad_summarize_prompt, zammad_tag_prompt
from errors import Result
from settings import Settings



##################################################
#                 COMMAND CLASS                  #
##################################################
class ZammadCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()
    zammad: ZammadAPI = ZammadAPI(settings.zammad_base_url, settings.zammad_api_token)

    if len(commands) > 1:
      if commands[1] == "list" or commands[1] == "query":
        if len(commands) > 2:
          print(zammad.list_tickets(commands[2]))
        else:
          print(zammad.list_tickets())
      elif commands[1] == "details" and len(commands) > 2:
        print(zammad.get_ticket_details(commands[2]))
      elif commands[1] == "test" and len(commands) > 2:
        print(zammad.get(commands[2]))
      elif commands[1] == "process":
        zammad_run_process(settings, zammad)
      elif commands[1] == "untag":
        zammad_remove_ai_tags(settings, zammad)
      else:
        help.unrecognizedCommand()
    else:
      help.zammadCommands()

    return result

def zammad_run_process(settings: Settings, zammad: ZammadAPI) -> Result:
  tickets = zammad.list_tickets("untagged-tickets")
  temp_tickets = tickets[11:]  # Select the first ticket for demonstration purposes

  for selected_ticket in temp_tickets:
    ticket_details = zammad.get_ticket_details(selected_ticket)
    tagging_messages = [
      {"role": "system", "content": zammad_tag_prompt},
      {"role": "user", "content": ticket_details}
    ]

    print("-" * 50)
    print("-" * 50)
    print(f"RAW TICKET DATA:\n{ticket_details}")

    tagging_result = model_run(settings.active_model, tagging_messages, settings=settings)
    if tagging_result.is_error():
      print(f"Error running tagging model: {tagging_result.get_message()}")
    else:
      print("-" * 50)
      print(f"Tagging Result:\n{tagging_result.data}")
      print("-" * 50)
      # Remove any escape characters and check for tags
      if tagging_result.data:
        cleaned_response = tagging_result.data.replace("\\", "")
        try:
          if cleaned_response and "[TAG]" in cleaned_response and "[/TAG]" in cleaned_response:
            start = cleaned_response.index("[TAG]") + len("[TAG]")
            end = cleaned_response.index("[/TAG]")
            tag = cleaned_response[start:end].strip()

            if tag in ["Phishing", "Spam", "Completed", "NetworkHardware", "Jenzabar", "LMS", "Report", "Printers", "Forms", "Adobe", "InfoMaker", "Salesforce", "Classroom", "Login", "Student", "Filter", "Video", "NoCategoryFound"]:
              zammad.add_tag(selected_ticket, f"AI-{tag}")
            else:
              zammad.add_tag(selected_ticket, "AI-Unknown")
          else:
            print("Missing tag markers in response, using AI-Blank")
            zammad.add_tag(selected_ticket, "AI-Blank")
        except Exception as e:
          print(f"Error extracting tag: {e}, using AI-Error")
          zammad.add_tag(selected_ticket, "AI-Error")

        zammad.add_tag(selected_ticket, "AI-Tagged")

def zammad_remove_ai_tags(settings: Settings, zammad: ZammadAPI) -> Result:
  result: Result = Result()
  tickets = zammad.list_tickets("tagged-tickets")
  
  if not tickets:
    print("No tagged tickets found")
    return result
    
  print(f"Found {len(tickets)} tagged tickets. Processing...")
  removed_count = 0
  
  for ticket_id in tickets:
    tags = zammad.list_tags(ticket_id)
    ai_tags = [tag for tag in tags if tag.startswith("AI-")]
    
    if ai_tags:
      print(f"\nRemoving {len(ai_tags)} AI tags from ticket {ticket_id}:")
      for tag in ai_tags:
        if zammad.remove_tag(ticket_id, tag):
          removed_count += 1
  
  print(f"\nCompleted! Removed {removed_count} AI tags from {len(tickets)} tickets")
  return result

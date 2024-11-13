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
    summary_messages = [
      {"role": "system", "content": zammad_summarize_prompt},
      {"role": "user", "content": ticket_details}
    ]
    tagging_messages = [
      {"role": "system", "content": zammad_tag_prompt},
    ]

    print("-" * 50)
    print("-" * 50)
    print(f"RAW TICKET DATA:\n{ticket_details}")

    # summarize ticket
    summary_result = model_run(settings.active_model, summary_messages, settings=settings)

    if summary_result.is_error():
      print(f"Error running summary model: {summary_result.get_message()}")
    else:
      print("-" * 50)
      print(f"Summary Result:\n{summary_result.data}")
      print("-" * 50)
      print(f"RAW TICKET DATA:\n{ticket_details}")

      # tag ticket
      tagging_messages.append({"role": "user", "content": summary_result.data + "\n\n\nRAW TICKET DATA\n" + ("-" * 50) + ticket_details})
      tagging_result = model_run(settings.active_model, tagging_messages, settings=settings)
      if tagging_result.is_error():
        print(f"Error running tagging model: {tagging_result.get_message()}")
      else:
        print("-" * 50)
        print(f"Tagging Result:\n{tagging_result.data}")
        print("-" * 50)
        if tagging_result.data and "[TAG]" in tagging_result.data:
          start = tagging_result.data.index("[TAG]") + len("[TAG]")
          end = tagging_result.data.index("[/TAG]")
          tag = tagging_result.data[start:end]

          if tag in ["Phishing", "Spam", "Completed", "NetworkHardware", "Jenzabar", "LMS", "Report", "Printers", "Forms", "Adobe", "InfoMaker", "Salesforce", "Classroom", "Login", "Student", "Filter", "Video", "NoCategoryFound"]:
            zammad.add_tag(selected_ticket, f"AI-{tag}")
          else:
            zammad.add_tag(selected_ticket, "AI-Unknown")

          zammad.add_tag(selected_ticket, "AI-Tagged")

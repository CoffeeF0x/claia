from commands.base import Command
from errors import Result
from settings import Settings
from typing import Dict



##################################################
#                 COMMAND CLASS                  #
##################################################
class CharacterCommand(Command):
  def execute(self, commands: list[str], settings: Settings) -> Result:
    result: Result = Result()

    if len(commands) > 1:
      if commands[1] == "list" and len(commands) > 2:
        list_characters(settings, commands[2])
      elif commands[1] == "list":
        list_characters(settings)
      elif commands[1] in ["remove", "unset"]:
        remove_character(settings)
      elif commands[1] in ["set", "select"] and len(commands) > 2:
        set_character(commands[2], settings)
      elif commands[1] in ["set", "select"]:
        print("No character selected")
      elif commands[1] in ["print", "current"]:
        current_character(settings)
      else:
        self.unrecognizedCommand()
    else:
      self.help()

    return result

  def help(self) -> None:
    print("Here are the available character commands:")
    print("  list <optional: character>")
    print("    - list all available characters or details about a specific character")
    print("  remove, unset <character>")
    print("    - remove the current character selection")
    print("  set, select <character>")
    print("    - select a character to use in the conversation")
    print("  print, current")
    print("    - display the current character selection")



##################################################
#                   FUNCTIONS                    #
##################################################
# Print currently selected character
def current_character(settings: Settings):
  if settings.active_prompt:
    print(f"Current character: {settings.active_prompt.title}")
  else:
    print("No character selected")

# List the available characters
def list_characters(settings: Settings, character_name: str = "") -> None:
  if character_name:
    prompt = next((p for p in settings.prompt_store if p.name == character_name), None)
    if prompt:
      print(f"Name: {prompt.name}")
      print(f"Title: {prompt.title}")
      print(f"Prompt: {prompt.prompt}")
      if prompt.description:
        print(f"Description: {prompt.description}")
    else:
      print(f"Character '{character_name}' not found")
  else:
    for prompt in settings.prompt_store:
      print(f"{prompt.name}: {prompt.title}")

# Remove character prompt
def remove_character(settings: Settings) -> None:
  settings.active_prompt = None
  print("Active character removed")

# Set the selected character
def set_character(character_name: str, settings: Settings):
  prompt = settings.get_prompt(character_name)
  if prompt:
    settings.active_prompt = prompt
    print(f"Selected character: {settings.active_prompt.title}")
  else:
    print(f"Character '{character_name}' not found")
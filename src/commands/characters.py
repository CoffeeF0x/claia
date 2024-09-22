import json, os
import help

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
        listCharacters(settings, commands[2])
      elif commands[1] == "list":
        listCharacters(settings)
      elif commands[1] in ["remove", "unset"]:
        removeCharacter(settings)
      elif commands[1] in ["set", "select"] and len(commands) > 2:
        setCharacter(commands[2], settings)
      elif commands[1] in ["set", "select"]:
        print("No character selected")
      elif commands[1] in ["print", "current"]:
        currentCharacter(settings)
      else:
        help.unrecognizedCommand()
    else:
      help.characterCommands()

    return result



##################################################
#                   FUNCTIONS                    #
##################################################
# Print currently selected character
def currentCharacter(settings: Settings):
  if settings.active_prompt:
    print(settings.active_prompt.title)
  else:
    print("No character selected")

# Return a list of all characters
def getCharacters(settings: Settings) -> list[Dict[str, str]]:
  characters = []
  for filename in os.listdir(settings.prompt_store_directory):
    if filename.endswith('.json'):
      full_path = os.path.join(settings.prompt_store_directory, filename)
      with open(full_path, 'r') as file:
        data = json.load(file)
        characters.append({"name": data["name"], "title": data["title"]})
  return characters

# List the available characters
def listCharacters(settings: Settings, character_name: str = "") -> None:
  characters = getCharacters(settings)
  if character_name:
    prompt_store = settings.active_prompt.load(character_name, settings.prompt_store_directory)
    print(f"Name: {prompt_store.name}")
    print(f"Title: {prompt_store.title}")
    print(f"Prompt: {prompt_store.prompt}")
    if prompt_store.description:
      print(f"Description: {prompt_store.description}")
  else:
    for character in characters:
      print(f"{character['name']}")

# Remove character prompt
def removeCharacter(settings: Settings) -> None:
  settings.active_prompt = None

# Set the selected character
def setCharacter(character_name: str, settings: Settings):
  try:
    settings.active_prompt = settings.active_prompt.load_by_name(character_name, settings.prompt_store_directory)
    print(f"Selected character: {settings.active_prompt.title}")
  except FileNotFoundError:
    print("Chosen character not found")

from commands.base import Command
from errors import Result
from settings import Settings
import help



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
def getCharacters(settings: Settings) -> list[str]:
  return settings.active_prompt.list_files(settings.prompt_store_directory)

# List the available characters
def listCharacters(settings: Settings, character_id: str = "") -> None:
  characters = getCharacters(settings)
  if character_id:
    if character_id in characters:
      prompt_store = settings.active_prompt.load(f"{character_id}.json", settings.prompt_store_directory)
      print(f"Title: {prompt_store.title}")
      print(f"Prompt: {prompt_store.prompt}")
      if prompt_store.description:
        print(f"Description: {prompt_store.description}")
    else:
      print(f"Character with ID {character_id} not found")
  else:
    for character in characters:
      prompt_store = settings.active_prompt.load(character, settings.prompt_store_directory)
      print(f"{prompt_store.unique_id}: {prompt_store.title}")

# Remove character prompt
def removeCharacter(settings: Settings) -> None:
  settings.active_prompt = None

# Set the selected character
def setCharacter(character_id: str, settings: Settings):
  characters = getCharacters(settings)
  if f"{character_id}.json" in characters:
    settings.active_prompt = settings.active_prompt.load(f"{character_id}.json", settings.prompt_store_directory)
    print(f"Selected character: {settings.active_prompt.title}")
  else:
    print("Chosen character not found")

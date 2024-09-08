from commands.base import Command
from errors import Result
from settings import Settings



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
  if settings.selected_character:
    print(settings.selected_character)
  else:
    print("No character selected")

# Return a list of all characters
def getCharacters(settings: Settings) -> list[str]:
  return list(settings.characters.keys())

# List the available characters
def listCharacters(settings: Settings, characterName: str = "") -> None:
  if characterName:
    print(settings.characters[characterName]["content"])
  else:
    for key in settings.characters:
      print(key)

# Remove character prompt
def removeCharacter(settings: Settings) -> None:
  settings.selected_character = ""

# Set the selected character
def setCharacter(character: str, settings: Settings):
  if character in getCharacters(settings):
    settings.selected_character = character
  else:
    print("Chosen character not found")

from abc import ABC, abstractmethod

# Internal dependencies
from errors import Result
from settings import Settings



##################################################
#                   BASE CLASS                   #
##################################################
class Command(ABC):
  # Abstract method to contain command logic for each child class
  @abstractmethod
  def execute(self, commands: list[str], settings: Settings) -> Result:
    pass

  # Optional method to provide help information for the command
  def help(self) -> None:
    pass

  # Method to display unrecognized command message
  def unrecognizedCommand(self) -> None:
    print("Command incomplete or not recognized")

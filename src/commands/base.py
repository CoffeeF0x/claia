from abc import ABC, abstractmethod

# Internal dependencies
from errors import Result
from settings import Settings



##################################################
#                   BASE CLASS                   #
##################################################
class Command(ABC):
  global command_registry

  # Abstract method to contain command logic for each child class
  @abstractmethod
  def execute(self, commands: list[str], settings: Settings) -> Result:
    pass

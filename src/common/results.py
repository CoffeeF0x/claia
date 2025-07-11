# External dependencies
from typing import Any



########################################################################
#                              RESULT                                  #
########################################################################
class Result:
  def __init__(self, success: bool = True, data: Any = None, message: str = None, fatal: bool = False, exit: bool = False, exit_code: int = 0):
    self.success = success
    self.data = data
    self.message = message
    self.fatal = fatal
    self.exit = exit
    self.exit_code = exit_code

  def is_success(self) -> bool:
    return self.success

  def is_error(self) -> bool:
    return not self.success

  def is_fatal(self) -> bool:
    return self.fatal

  def is_exit(self) -> bool:
    return self.exit

  def get_data(self) -> Any:
    return self.data

  def get_message(self) -> str:
    return self.message

  def get_exit_code(self) -> int:
    return self.exit_code

  def __str__(self) -> str:
    if self.success:
      return f"Success: {self.data}"
    else:
      return f"Error: {self.message}"

  @staticmethod
  def ok(data: Any = None) -> 'Result':
    return Result(True, data)

  @staticmethod
  def fail(message: str, data: Any = None) -> 'Result':
    return Result(success=False, data=data, message=message)

  @staticmethod
  def shutdown(message: str = "Shutting down", exit: bool = True, exit_code: int = 0) -> 'Result':
    return Result(message=message, exit=exit, exit_code=exit_code)

from os import name, system

# Clear the console
def clear() -> None:
  if name == "posix":
    system("clear")
  else:
    system("cls")

# No print statement should ever output more than 72 characters per console line

def unrecognizedCommand() -> None:
  print("Command incomplete or not recognized")

def listCommands() -> None:
  print("Here are the sub commands for list:")
  print("  characters")
  print("    - list all characters")
  print("  characters <characterName>")
  print("    - list the specified character's prompt")
  print("  conversations")
  print("    - list all stored conversations without the .json file extension")

def allCommands() -> None:
  pass

def characterCommands() -> None:
  pass

def conversationCommands() -> None:
  pass

def systemCommands() -> None:
  pass

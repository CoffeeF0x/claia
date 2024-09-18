# NOTE: No print statement should ever output more than 72 characters per console line

def unrecognizedCommand() -> None:
  print("Command incomplete or not recognized")

def allCommands() -> None:
  print("Here is a list of available commands:")
  print("  system, sys, s")
  print("    - technical commands such as exiting the program and clearing the screen")
  print("  character, characters")
  print("    - commands related to characters or system promts")
  print("  conversation, conversations")
  print("    - commands related to conversations and saved messages")
  print("  model, models")
  print("    - commands related to selecting and managing language models")

def characterCommands() -> None:
  print("Here are the available character commands:")
  print("  list <optional: character>")
  print("    - list all available characters or details about a specific character")
  print("  remove, unset <character>")
  print("    - remove the current character selection")
  print("  set, select <character>")
  print("    - select a character to use in the conversation")
  print("  print, current")
  print("    - display the current character selection")

def conversationCommands() -> None:
  print("Here are the available conversation commands:")
  print("  list")
  print("    - list any saved conversations")
  print("  new")
  print("    - start a new conversation")
  print("  print")
  print("    - display the current conversation")
  print("  load <filename>")
  print("    - load a saved conversation")

def expirimentalCommands() -> None:
  print("Here are the available expirimental commands:")

def modelCommands() -> None:
  print("Here are the available model commands:")
  print("  list")
  print("    - list all available models")
  print("  list <model>")
  print("    - display details about a specific model")
  print("  set, select <model>")
  print("    - select a model to use for generation")
  print("  print, current")
  print("    - display the current model selection")

def systemCommands() -> None:
  print("Here are the available system commands:")
  print("  clear, cls, c")
  print("    - clear the screen")
  print("  quit, exit, q")
  print("    - terminate the clai software")

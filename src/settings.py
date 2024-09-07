import os
import uuid

class Settings:
  openAiApiToken: str = ""
  anthropicApiToken: str = ""
  localLlmApiToken: str = ""
  localLlmBaseUrl: str = ""
  selectedLlm: str = "0"
  selectedConversation: str = f"{str(uuid.uuid4())}.json"
  selectedCharacter: str = "writer"
  conversationDirectory: str = "history"
  conversation: list[str] = []
  characters = {
    "default": {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
    "writer": {"role": "system", "content": "You are a brilliant writer, always adding events and details that give life to the story, making sure to show and not tell about environments, characters, and actions."}
  }

  def __init__(self):
    self.loadEnv()

  def loadEnv(self) -> bool:
    success: bool = True

    if "TOKEN_OPENAI" in os.environ:
      self.openAiApiToken = os.environ["TOKEN_OPENAI"]
    else:
      success = False
      print("No OpenAI API Token found")

    if "TOKEN_ANTHROPIC" in os.environ:
      self.anthropicApiToken = os.environ["TOKEN_ANTHROPIC"]
    else:
      success = False
      print("No Anthropic API Token found")

    if "TOKEN_LOCAL" in os.environ:
      self.localLlmApiToken = os.environ["TOKEN_LOCAL"]
    else:
      success = False
      print("No LocalLLM API Token found")

    if "LOCALLLM_BASEURL" in os.environ:
      self.localLlmBaseUrl = os.environ["LOCALLLM_BASEURL"]
    else:
      success = False
      print("No LocalLLM Base URL found")

    self.selectedCharacter = os.environ.get("SELECTED_CHARACTER") or self.selectedCharacter
    self.conversationDirectory = os.environ.get("CONVERSATION_DIRECTORY") or self.conversationDirectory
    self.selectedConversation = os.environ.get("SELECTED_CONVERSATION") or self.selectedConversation

    return success

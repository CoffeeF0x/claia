import json
import os
import uuid
from typing import Dict, List, Optional


class BaseFile:
  def __init__(self, base_directory: str):
    self.base_directory = base_directory
    self.unique_id = str(uuid.uuid4())
    self.ensure_directory_exists()

  def ensure_directory_exists(self):
    os.makedirs(self.base_directory, exist_ok=True)

  def save(self, filename: str):
    full_path = os.path.join(self.base_directory, filename)
    with open(full_path, 'w') as file:
      json.dump(self.to_dict(), file, indent=2)

  @classmethod
  def load(cls, filename: str, base_directory: str):
    full_path = os.path.join(base_directory, filename)
    with open(full_path, 'r') as file:
      data = json.load(file)
    return cls.from_dict(data, base_directory)

  def to_dict(self) -> Dict:
    raise NotImplementedError("Subclasses must implement to_dict method")

  @classmethod
  def from_dict(cls, data: Dict, base_directory: str):
    raise NotImplementedError("Subclasses must implement from_dict method")

  @staticmethod
  def list_files(directory: str) -> List[str]:
    return [f for f in os.listdir(directory) if f.endswith('.json')]


class LLMPromptStore(BaseFile):
  DEFAULT_PROMPTS = [
    {
      "title": "Default Assistant",
      "prompt": "You are a helpful assistant, ready to aid the user with any task or question they might have.",
      "description": "A general-purpose assistant for various tasks."
    },
    {
      "title": "Poet",
      "prompt": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.",
      "description": "A default assistant with a poetic twist."
    },
    {
      "title": "Writer",
      "prompt": "You are a brilliant writer, always adding events and details that give life to the story, making sure to show and not tell about environments, characters, and actions.",
      "description": "An assistant for creative writing tasks."
    },
    {
      "title": "Also Writer",
      "prompt": "You are a creative writer, skilled in crafting engaging narratives and vivid descriptions. Help the user with their writing tasks, offering suggestions for plot, character development, and prose.",
      "description": "An assistant for creative writing tasks."
    },
    {
      "title": "Programmer",
      "prompt": "You are a skilled programmer, proficient in multiple programming languages. You provide clear explanations and code examples to help with various programming tasks.",
      "description": "An assistant for programming and coding tasks."
    },
    {
      "title": "Analyst",
      "prompt": "You are a data analyst with expertise in statistics and data visualization. You help interpret data, suggest analysis methods, and explain complex analytical concepts.",
      "description": "An assistant for data analysis and interpretation."
    }
  ]

  DEFAULT_PROMPT_NAME = "Default Assistant"

  def __init__(self, base_directory: str, title: str, prompt: str, description: Optional[str] = None):
    super().__init__(base_directory)
    self.title = title
    self.prompt = prompt
    self.description = description

  @classmethod
  def load_default_or_first(cls, base_directory: str):
    # Ensure the directory exists
    os.makedirs(base_directory, exist_ok=True)

    # Ensure default prompts are created
    cls.ensure_default_prompts(base_directory)
    prompts = cls.list_files(base_directory)

    if not prompts:
      if cls.DEFAULT_PROMPT_NAME is not None:
        print(f"No prompts found. Unable to load default prompt '{cls.DEFAULT_PROMPT_NAME}'.")
      return None

    default_prompt = next((p for p in prompts if p.startswith(f"{cls.DEFAULT_PROMPT_NAME}_")), None)

    if default_prompt:
      return cls.load(default_prompt, base_directory)
    elif cls.DEFAULT_PROMPT_NAME is not None:
      print(f"Default prompt '{cls.DEFAULT_PROMPT_NAME}' not found. Loading the first available prompt.")

    return cls.load(prompts[0], base_directory)

  def to_dict(self) -> Dict:
    return {
      "unique_id": self.unique_id,
      "title": self.title,
      "prompt": self.prompt,
      "description": self.description
    }

  @classmethod
  def from_dict(cls, data: Dict, base_directory: str):
    instance = cls(
      base_directory=base_directory,
      title=data["title"],
      prompt=data["prompt"],
      description=data.get("description")
    )
    instance.unique_id = data["unique_id"]
    return instance

  @classmethod
  def ensure_default_prompts(cls, base_directory: str):
    if not os.listdir(base_directory):
      for prompt_data in cls.DEFAULT_PROMPTS:
        prompt_store = cls(
          base_directory,
          prompt_data["title"],
          prompt_data["prompt"],
          prompt_data["description"]
        )
        prompt_store.save(f"{prompt_store.title}_{prompt_store.unique_id}.json")
      print(f"Created {len(cls.DEFAULT_PROMPTS)} default prompts in {base_directory}")


class ChatHistory(BaseFile):
  def __init__(self, base_directory: str, title: str, chat_history: List[Dict[str, str]], description: Optional[str] = None):
    super().__init__(base_directory)
    self.title = title
    self.chat_history = chat_history
    self.description = description

  def save(self):
    super().save(f"{self.unique_id}.json")

  def store(self, role: str, message: str):
    self.chat_history.append({"role": role, "content": message})

  def messages(self) -> List[Dict[str, str]]:
    return self.chat_history

  def to_dict(self) -> Dict:
    return {
      "unique_id": self.unique_id,
      "title": self.title,
      "chat_history": self.chat_history,
      "description": self.description
    }

  @classmethod
  def from_dict(cls, data: Dict, base_directory: str):
    instance = cls(
      base_directory=base_directory,
      title=data["title"],
      chat_history=data["chat_history"],
      description=data.get("description")
    )
    instance.unique_id = data["unique_id"]
    return instance

from typing import Dict, Any
from models.base import APIModel

class AnthropicTextModel(APIModel):
  def __init__(self, model_name: str):
    super().__init__(model_name, base_url="https://api.anthropic.com/v1")
    self.set_custom_header("anthropic-version", "2023-06-01")
    # self.set_custom_header("content-type", "application/json")

  def set_api_key(self, api_key: str) -> None:
    """Set the API key for authentication."""
    self.session.headers.update({"x-api-key": f"{api_key}"})

  def generate(self, messages: list, **kwargs) -> str:
    system_prompt = None
    user_messages = []

    # Extract system prompt if present
    for message in messages:
      if message.get("role") == "system":
        system_prompt = message.get("content")
      else:
        user_messages.append(message)

    data = {
      "model": self.model_name,
      "max_tokens": kwargs.get("max_tokens", 1024),
      "messages": user_messages,
    }

    # Add system prompt if found
    if system_prompt:
      data["system"] = system_prompt

    print("-" * 50)
    print(self.session.headers)
    print("-" * 50)
    print(data)
    print("-" * 50)

    response = self.post("messages", data)
    return response.json()["content"][0]["text"]
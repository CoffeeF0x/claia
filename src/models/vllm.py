from typing import Dict, Any
from models.base import APIModel

class VLLMTextModel(APIModel):
  def __init__(self, model_name: str, base_url: str = None):
    if not base_url:
      raise ValueError("VLLM requires a base URL to be specified")
    super().__init__(model_name, base_url=base_url)

  def generate(self, messages: list, **kwargs) -> str:
    # # Convert chat messages to prompt format
    # prompt = ""
    # for msg in messages:
    #   role = msg.get("role", "")
    #   content = msg.get("content", "")
      
    #   if role == "system":
    #     prompt += f"{content}\n"
    #   elif role == "user":
    #     prompt += f"User: {content}\n"
    #   elif role == "assistant":
    #     prompt += f"Assistant: {content}\n"
    
    # # Add final user prompt indicator if last message was from user
    # if messages[-1]["role"] == "user":
    #   prompt += "Assistant: "

    data = {
      "messages": messages,
      "model": self.model_name,
      "max_tokens": kwargs.get("max_tokens", 100),
      "temperature": kwargs.get("temperature", 0.7),
      "top_p": kwargs.get("top_p", 1.0),
      "stream": kwargs.get("stream", False),
      "stop": kwargs.get("stop", None),
    }
    
    response = self.post("v1/chat/completions", data)
    return response.json()["choices"][0]["message"]["content"]
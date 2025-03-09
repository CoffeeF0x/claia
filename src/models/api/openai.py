from typing import Dict, Any
import logging

# Internal dependencies
from models.base import APIModel



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class OpenAITextModel(APIModel):
  def __init__(self, model_name: str):
    super().__init__(model_name, base_url="https://api.openai.com/v1")

  def generate(self, messages: list, **kwargs) -> str:
    data = {
      "model": self.model_name,
      "messages": messages,
      "max_tokens": kwargs.get("max_tokens", 100),
      "temperature": kwargs.get("temperature", 0.7),
      "top_p": kwargs.get("top_p", 1.0),
      "n": kwargs.get("n", 1),
      "stream": kwargs.get("stream", False),
      "stop": kwargs.get("stop", None),
    }
    response = self.post("chat/completions", data)
    return response.json()["choices"][0]["message"]["content"]

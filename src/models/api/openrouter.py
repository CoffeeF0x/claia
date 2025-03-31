from typing import Dict, Any
import logging

# Internal dependencies
from ..base import APIModel



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class OpenRouterModel(APIModel):
  def __init__(self, model_name: str):
    super().__init__(model_name, base_url="https://openrouter.ai/api/v1")
    # self.set_custom_header("HTTP-Referer", "http://localhost:3000")  # Should be configurable
    # self.set_custom_header("X-Title", "Local Development")  # Should be configurable

  def generate(self, messages: list, **kwargs) -> str:
    data = {
      "model": self.model_name,
      "messages": messages,
      "max_tokens": kwargs.get("max_tokens", 100),
      "temperature": kwargs.get("temperature", 0.7),
      "top_p": kwargs.get("top_p", 1.0),
      "stream": kwargs.get("stream", False),
      "stop": kwargs.get("stop", None),
    }
    response = self.post("chat/completions", data)
    return response.json()["choices"][0]["message"]["content"]

from typing import Dict, Any
import logging

# Internal dependencies
from ..base import APIModel
from files import Conversation
from enums import MessageRole

########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class OpenAIModel(APIModel):
  def __init__(self, model_name: str):
    super().__init__(model_name, base_url="https://api.openai.com/v1")

  def generate(self, conversation: Conversation, **kwargs) -> str:
    # Get messages and add system prompt if present
    messages = []

    # Add system prompt if available
    if conversation.prompt:
      messages.append({
        "role": "system",
        "content": conversation.prompt
      })

    # Get user and assistant messages
    conversation_messages = conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT])

    # Convert to OpenAI format
    for message in conversation_messages:
      messages.append({
        "role": message.speaker.value,
        "content": message.content
      })

    logger.debug(f"Sending {len(messages)} messages to OpenAI API")

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
    response_text = response.json()["choices"][0]["message"]["content"]

    # Add the response as an assistant message to the conversation
    conversation.add_message(MessageRole.ASSISTANT, response_text)

    return response_text
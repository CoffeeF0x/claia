from typing import Dict, Any, List
import logging
import json

# Internal dependencies
from ..base import APIModel
from claia.lib.data import Conversation
from claia.lib.enums.conversation import MessageRole



########################################################################
#                              CONSTANTS                               #
########################################################################
# Openrouter-specific default settings
DEFAULT_SETTINGS = {
  "max_tokens": 1000,
}

# Header defaults
DEFAULT_HTTP_REFERER = "http://localhost:3000"
DEFAULT_X_TITLE = "CLAIA"



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
    # Required OpenRouter headers
    self.set_custom_header("HTTP-Referer", DEFAULT_HTTP_REFERER)
    self.set_custom_header("X-Title", DEFAULT_X_TITLE)

  def _format_messages(self, conversation: Conversation) -> List[Dict[str, Any]]:
    """
    Format conversation messages for the OpenRouter API.

    Args:
        conversation: The conversation containing messages

    Returns:
        List[Dict[str, Any]]: Formatted messages for the API request
    """
    messages = []

    # Add merged system prompt (includes tool instructions if present)
    system_prompt = conversation.get_system_prompt()
    if system_prompt:
      messages.append({
        "role": "system",
        "content": system_prompt
      })

    # Convert to OpenAI format
    for message in conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT]):
      messages.append({
        "role": message.speaker.value,
        "content": message.content
      })

    logger.debug(f"Sending {len(messages)} messages to OpenRouter API")
    return messages

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """
    Generate a response using the OpenRouter API.

    Args:
        conversation: The conversation containing messages and settings
        **kwargs: Additional keyword arguments to override settings

    Returns:
        str: The generated response text
    """
    settings = self.update_settings(DEFAULT_SETTINGS, conversation, **kwargs)
    messages = self._format_messages(conversation)

    # Prepare the API request data
    data = {
      "model": self.model_name,
      "messages": messages,
      "max_tokens": settings.get("max_tokens"),
      "stream": settings.get("stream")
    }

    # Add optional parameters if they exist in settings
    if settings.get("temperature"):
      data["temperature"] = settings.get("temperature")
    if settings.get("top_p"):
      data["top_p"] = settings.get("top_p")
    if settings.get("top_k"):
      data["top_k"] = settings.get("top_k")
    if settings.get("presence_penalty"):
      data["presence_penalty"] = settings.get("presence_penalty")
    if settings.get("frequency_penalty"):
      data["frequency_penalty"] = settings.get("frequency_penalty")
    if settings.get("stop"):
      data["stop"] = settings.get("stop")
    if settings.get("n"):
      data["n"] = settings.get("n")

    # Call the appropriate method based on whether streaming is enabled
    if settings.get("stream"):
      return self._get_text_stream(data, conversation)
    else:
      return self._get_text(data, conversation)

  def _get_text_stream(self, data: Dict[str, Any], conversation: Conversation) -> str:
    """
    Get streaming response from the OpenRouter API.

    Args:
        data: The request payload
        conversation: The conversation to update with streamed content

    Returns:
        str: The complete generated text
    """
    message = conversation.add_message(MessageRole.ASSISTANT, "")
    response = self.post("chat/completions", data, stream=True)

    # Process the streaming response
    for line in response.iter_lines():
      if not line:
        continue

      line = line.decode('utf-8') if isinstance(line, bytes) else line

      if not line.startswith('data: '):
        continue

      data_line = line[6:]

      if data_line == '[DONE]':
        break

      try:
        chunk = json.loads(data_line)

        if 'choices' in chunk and len(chunk['choices']) > 0:
          delta = chunk['choices'][0].get('delta', {})

          if 'content' in delta:
            content_chunk = delta['content']
            conversation.stream_message(message.message_id, content_chunk, append=True)

      except json.JSONDecodeError:
        logger.warning(f"Failed to parse streaming response: {data_line}")

    # Finish the stream with a newline and return the message content
    conversation.stream_message(message.message_id, "\n", append=True, end=True)
    return message.content

  def _get_text(self, data: Dict[str, Any], conversation: Conversation) -> str:
    """
    Get non-streaming response from the OpenRouter API.

    Args:
        data: The request payload
        conversation: The conversation to update with the response

    Returns:
        str: The generated text
    """

    # Initialize an empty response text
    response_text = ""

    response = self.post("chat/completions", data)
    response_json = response.json()

    if 'choices' in response_json and len(response_json['choices']) > 0:
      response_text = response_json["choices"][0]["message"]["content"]

      # Add the response as an assistant message to the conversation
      conversation.add_message(MessageRole.ASSISTANT, response_text)

      return response_text
    else:
      logger.error(f"Unexpected response format from OpenRouter: {response_json}")
      error_message = "Error: Invalid response from OpenRouter API"
      return error_message

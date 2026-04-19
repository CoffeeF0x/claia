from typing import Dict, Any, List, Generator
import logging
import json

# Internal dependencies
from ..base import APIModel
from claia_core.data import Conversation
from claia_core.enums.conversation import MessageRole



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
    self.set_custom_header("HTTP-Referer", DEFAULT_HTTP_REFERER)
    self.set_custom_header("X-Title", DEFAULT_X_TITLE)

  def _format_messages(self, conversation: Conversation) -> List[Dict[str, Any]]:
    """Format conversation messages for the OpenRouter API."""
    messages = []

    system_prompt = conversation.get_system_prompt()
    if system_prompt:
      messages.append({
        "role": "system",
        "content": system_prompt
      })

    for message in conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT]):
      messages.append({
        "role": message.speaker.value,
        "content": message.content
      })

    logger.debug(f"Sending {len(messages)} messages to OpenRouter API")
    return messages

  def generate(self, conversation: Conversation, **kwargs) -> Generator[str, None, str]:
    """Generate a response using the OpenRouter API. Yields tokens, returns full response."""
    try:
      settings = self.update_settings(DEFAULT_SETTINGS, conversation, **kwargs)
      messages = self._format_messages(conversation)

      data = {
        "model": self.model_name,
        "messages": messages,
        "max_tokens": settings.get("max_tokens"),
        "stream": settings.get("stream")
      }

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

      if settings.get("stream"):
        full_response = yield from self._get_text_stream(data)
      else:
        full_response = yield from self._get_text(data)

      return full_response

    except Exception as e:
      logger.error(f"Error generating response with OpenRouter model {self.model_name}: {e}")
      error_msg = f"Error: {str(e)}"
      yield error_msg
      return error_msg

  def _get_text_stream(self, data: Dict[str, Any]) -> Generator[str, None, str]:
    """Stream response from the OpenRouter API. Yields tokens, returns full response."""
    try:
      response = self.post("chat/completions", data, stream=True)
      full_response = ""

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
              full_response += content_chunk
              yield content_chunk

        except json.JSONDecodeError:
          logger.warning(f"Failed to parse streaming response: {data_line}")

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      error_msg = f"Streaming error: {str(e)}"
      yield error_msg
      return error_msg

  def _get_text(self, data: Dict[str, Any]) -> Generator[str, None, str]:
    """Get non-streaming response from the OpenRouter API. Yields full content as single token."""
    try:
      response = self.post("chat/completions", data)
      response_json = response.json()

      if 'choices' in response_json and len(response_json['choices']) > 0:
        response_text = response_json["choices"][0]["message"]["content"]
        yield response_text
        return response_text
      else:
        logger.error(f"Unexpected response format from OpenRouter: {response_json}")
        error_msg = "Error: Invalid response from OpenRouter API"
        yield error_msg
        return error_msg

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      error_msg = f"API error: {str(e)}"
      yield error_msg
      return error_msg

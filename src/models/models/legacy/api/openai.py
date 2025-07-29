from typing import Dict, Any, List
import logging
import json

# Internal dependencies
from ..base import APIModel
from common.files.conversation import Conversation
from common.enums.conversation import MessageRole



########################################################################
#                              CONSTANTS                               #
########################################################################
# OpenAI-specific default settings
DEFAULT_SETTINGS = {
  "max_tokens":  1000,
}



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

  def _format_messages(self, conversation: Conversation) -> List[Dict[str, Any]]:
    """
    Format conversation messages for the OpenAI API.

    Args:
        conversation: The conversation containing messages

    Returns:
        List[Dict[str, Any]]: Formatted messages for the API request
    """
    messages = []

    # Add system prompt if available
    if conversation.prompt:
      messages.append({
        "role": "system",
        "content": conversation.prompt
      })

    # Convert messages to OpenAI format
    for message in conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT]):
      messages.append({
        "role": message.speaker.value,
        "content": message.content
      })

    logger.debug(f"Sending {len(messages)} messages to OpenAI API")
    return messages

  def generate(self, conversation: Conversation, **kwargs) -> str:
    settings = self.update_settings(DEFAULT_SETTINGS, conversation, **kwargs)
    messages = self._format_messages(conversation)

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
    if settings.get("n"):
      data["n"] = settings.get("n")
    if settings.get("stop"):
      data["stop"] = settings.get("stop")
    if settings.get("presence_penalty"):
      data["presence_penalty"] = settings.get("presence_penalty")
    if settings.get("frequency_penalty"):
      data["frequency_penalty"] = settings.get("frequency_penalty")
    if settings.get("top_k"):
      data["top_k"] = settings.get("top_k")

    # Call the appropriate method based on whether streaming is enabled
    if settings.get("stream"):
      return self._get_text_stream(data, conversation)
    else:
      return self._get_text(data, conversation)

  def _get_text_stream(self, data: Dict[str, Any], conversation: Conversation) -> str:
    """
    Get streaming response from the OpenAI API.

    Args:
        data: The request payload
        conversation: The conversation to update with streamed content

    Returns:
        str: The complete generated text
    """
    # Add an empty assistant message to the conversation
    message = conversation.add_message(MessageRole.ASSISTANT, "")

    # Make a streaming request
    response = self.post("chat/completions", data, stream=True)

    # Process the streaming response
    for line in response.iter_lines():
      if line:
        line = line.decode('utf-8') if isinstance(line, bytes) else line
        if line.startswith('data: '):
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

    # Append a newline and mark the end of the stream
    conversation.stream_message(message.message_id, "\n", append=True, end=True)

    return message.content

  def _get_text(self, data: Dict[str, Any], conversation: Conversation) -> str:
    """
    Get non-streaming response from the OpenAI API.

    Args:
        data: The request payload
        conversation: The conversation to update with the response

    Returns:
        str: The generated text
    """
    response = self.post("chat/completions", data)
    response_text = response.json()["choices"][0]["message"]["content"]

    # Add the response as an assistant message to the conversation
    conversation.add_message(MessageRole.ASSISTANT, response_text)

    return response_text
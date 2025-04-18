from typing import Dict, Any, Optional
import logging
import json

# Internal dependencies
from ..base import APIModel
from files import Conversation
from enums import MessageRole



########################################################################
#                              CONSTANTS                               #
########################################################################
# API request defaults
OPENROUTER_DEFAULTS = {
  "max_tokens": 1000,
  "temperature": 0.7,
  "top_p": 1.0,
  "top_k": None,
  "presence_penalty": 0,
  "frequency_penalty": 0,
  "stop": None,
  "stream": True
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

  def _get_settings_from_conversation(self, conversation: Conversation) -> Dict[str, Any]:
    """
    Extract settings from the conversation object, falling back to defaults.

    Args:
        conversation: The conversation containing settings

    Returns:
        Dict[str, Any]: The settings dictionary with defaults applied where needed
    """
    # Start with our defaults
    settings = OPENROUTER_DEFAULTS.copy()

    # Get conversation settings if available
    conversation_settings = conversation.get_settings()
    if conversation_settings:
      # Override with streaming setting
      settings["stream"] = conversation_settings.streaming

      # Override with text settings if available
      text_settings = conversation_settings.text_settings
      if text_settings:
        if "max_tokens" in text_settings:
          settings["max_tokens"] = text_settings["max_tokens"]

        if "temperature" in text_settings:
          settings["temperature"] = text_settings["temperature"]

    return settings

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """
    Generate a response using the OpenRouter API.

    Args:
        conversation: The conversation containing messages and settings
        **kwargs: Additional keyword arguments to override settings

    Returns:
        str: The generated response text
    """
    # Get settings from conversation and apply additional overrides from kwargs
    settings = self._get_settings_from_conversation(conversation)
    settings.update({k: v for k, v in kwargs.items() if k in OPENROUTER_DEFAULTS})

    # Extract individual settings for clarity
    is_streaming = settings["stream"]
    max_tokens = settings["max_tokens"]
    temperature = settings["temperature"]
    top_p = settings["top_p"]
    top_k = settings["top_k"]
    presence_penalty = settings["presence_penalty"]
    frequency_penalty = settings["frequency_penalty"]
    stop = settings["stop"]

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

    logger.debug(f"Sending {len(messages)} messages to OpenRouter API")

    # Prepare the API request data
    data = {
      "model": self.model_name,
      "messages": messages,
      "max_tokens": max_tokens,
      "temperature": temperature,
      "top_p": top_p,
      "stream": is_streaming,
      "stop": stop,
    }

    # Add optional parameters only if they have a value
    if top_k is not None:
      data["top_k"] = top_k
    if presence_penalty != 0:
      data["presence_penalty"] = presence_penalty
    if frequency_penalty != 0:
      data["frequency_penalty"] = frequency_penalty

    # Handle streaming vs. non-streaming requests
    if is_streaming:
      # Add an empty assistant message to the conversation
      message_id = conversation.add_message(MessageRole.ASSISTANT, "").message_id

      # Make a streaming request
      buffer = ""
      with self.post("chat/completions", data, stream=True) as r:
        for chunk in r.iter_content(chunk_size=1024, decode_unicode=True):
          buffer += chunk
          while True:
            try:
              # Find the next complete SSE line
              line_end = buffer.find('\n')
              if line_end == -1:
                break
              line = buffer[:line_end].strip()
              buffer = buffer[line_end + 1:]
              if line.startswith('data: '):
                data = line[6:]
                if data == '[DONE]':
                  break
                try:
                  data_obj = json.loads(data)
                  content = data_obj["choices"][0]["delta"].get("content")
                  if content:
                    conversation.stream_message(message_id, content, append=True)
                    # print(content, end="", flush=True)
                except json.JSONDecodeError:
                  pass
            except Exception:
              break

      # Append a newline at the end of the streamed message and mark the end of stream
      conversation.stream_message(message_id, "\n", append=True, end=True)

      return buffer
    else:
      # Initialize an empty response text
      response_text = ""

      # Non-streaming request
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

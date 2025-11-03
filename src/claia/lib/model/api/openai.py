"""
OpenAI API model implementation.

This module provides the OpenAIModel class for interacting with OpenAI's API,
including support for streaming and non-streaming responses.
"""

import json
import logging
from typing import Dict, Any, Optional

# Internal dependencies
from claia.lib.results import Result
from claia.lib.data import Conversation
from claia.lib.enums.conversation import MessageRole
from ..base import APIModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class OpenAIModel(APIModel):
  """OpenAI API model implementation."""

  def __init__(self, model_name: str, openai_api_token: Optional[str] = None):
    super().__init__(model_name, "https://api.openai.com/v1")
    if openai_api_token:
      self.set_api_key(openai_api_token)

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """Generate a response using OpenAI's API."""
    try:
      # Get settings
      settings = self.update_settings({}, conversation, **kwargs)

      # Convert conversation to OpenAI format
      messages = self._convert_conversation_to_messages(conversation)

      # Prepare request data
      request_data = {
        "model": self.model_name,
        "messages": messages,
        **{k: v for k, v in settings.items() if v is not None}
      }

      # Make API request
      if settings.get("stream", False):
        return self._handle_streaming_response(request_data, conversation)
      else:
        return self._handle_non_streaming_response(request_data, conversation)

    except Exception as e:
      logger.error(f"Error generating response with OpenAI model {self.model_name}: {e}")
      return f"Error: {str(e)}"

  def _convert_conversation_to_messages(self, conversation: Conversation) -> list:
    """Convert a Conversation object to OpenAI messages format."""
    messages = []

    # Prepend merged system prompt (includes tool instructions if present)
    system_prompt = conversation.get_system_prompt()
    if system_prompt:
      messages.append({
        "role": "system",
        "content": system_prompt
      })

    for message in conversation.messages:
      # Skip any existing system messages; we already injected a merged system prompt above
      if message.speaker not in (MessageRole.USER, MessageRole.ASSISTANT):
        continue

      role_mapping = {
        MessageRole.USER: "user",
        MessageRole.ASSISTANT: "assistant"
      }

      openai_role = role_mapping.get(message.speaker, "user")
      messages.append({
        "role": openai_role,
        "content": message.content
      })

    return messages

  def _handle_streaming_response(self, request_data: Dict[str, Any], conversation: Conversation) -> str:
    """Handle streaming response from OpenAI API."""
    try:
      response = self.post("chat/completions", request_data, stream=True)

      full_response = ""

      # Add a blank assistant message to the conversation that we'll update
      message = conversation.add_message(MessageRole.ASSISTANT, "")

      for line in response.iter_lines():
        if line:
          line_text = line.decode('utf-8')
          if line_text.startswith('data: '):
            data_text = line_text[6:]  # Remove 'data: ' prefix

            if data_text.strip() == '[DONE]':
              break

            try:
              data = json.loads(data_text)
              if 'choices' in data and len(data['choices']) > 0:
                delta = data['choices'][0].get('delta', {})
                if 'content' in delta:
                  content = delta['content']
                  full_response += content
                  conversation.stream_message(message.message_id, content, append=True)
            except json.JSONDecodeError:
              continue

      # Mark the end of the stream
      conversation.stream_message(message.message_id, "", append=True, end=True)

      return full_response

    except Exception as e:
      logger.error(f"Error in streaming response: {e}")
      return f"Streaming error: {str(e)}"

  def _handle_non_streaming_response(self, request_data: Dict[str, Any], conversation: Conversation) -> str:
    """Handle non-streaming response from OpenAI API."""
    try:
      response = self.post("chat/completions", request_data)
      data = response.json()

      # Extract content
      content = ""
      if 'choices' in data and len(data['choices']) > 0:
        content = data['choices'][0]['message']['content']

      # Add message with content (could be an empty string if no content is returned)
      conversation.add_message(MessageRole.ASSISTANT, content)

      return content if content else "No response generated"

    except Exception as e:
      logger.error(f"Error in non-streaming response: {e}")
      return f"API error: {str(e)}"

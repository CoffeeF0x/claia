from typing import Dict, Any
import logging
import json

# Internal dependencies
from ..base import APIModel
from files import Conversation
from enums import MessageRole



########################################################################
#                              CONSTANTS                               #
########################################################################
MODEL_DEFAULTS = {
  "max_tokens":  1000,
  "temperature": 0.7,
  "top_p":       1.0,
  "n":           1,
  "stop":        None,
  "stream":      True
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

  def generate(self, conversation: Conversation, **kwargs) -> str:
    # Get messages and add system prompt if present
    messages = []
    is_streaming = kwargs.get("stream",      MODEL_DEFAULTS["stream"]     )
    max_tokens   = kwargs.get("max_tokens",  MODEL_DEFAULTS["max_tokens"] )
    temperature  = kwargs.get("temperature", MODEL_DEFAULTS["temperature"])
    top_p        = kwargs.get("top_p",       MODEL_DEFAULTS["top_p"]      )
    n            = kwargs.get("n",           MODEL_DEFAULTS["n"]          )
    stop         = kwargs.get("stop",        MODEL_DEFAULTS["stop"]       )

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
      "max_tokens": max_tokens,
      "temperature": temperature,
      "top_p": top_p,
      "n": n,
      "stream": is_streaming,
      "stop": stop,
    }

    if is_streaming:
      # Add an empty assistant message to the conversation
      message = conversation.add_message(MessageRole.ASSISTANT, "")

      # Make a streaming request
      response = self.post("chat/completions", data, stream=True)

      # Process the streaming response
      for line in response.iter_lines():
        if line:
          line = line.decode('utf-8') if isinstance(line, bytes) else line
          if line.startswith('data: '):
            data = line[6:]
            if data == '[DONE]':
              break
            try:
              chunk = json.loads(data)
              if 'choices' in chunk and len(chunk['choices']) > 0:
                delta = chunk['choices'][0].get('delta', {})
                if 'content' in delta:
                  content_chunk = delta['content']
                  conversation.stream_message(message.message_id, content_chunk, append=True)
            except json.JSONDecodeError:
              logger.warning(f"Failed to parse streaming response: {data}")

      # Append a newline and mark the end of the stream
      conversation.stream_message(message.message_id, "\n", append=True, end=True)

      return message.content

    else:
      # Non-streaming request
      response = self.post("chat/completions", data)
      response_text = response.json()["choices"][0]["message"]["content"]

      # Add the response as an assistant message to the conversation
      conversation.add_message(MessageRole.ASSISTANT, response_text)

      return response_text
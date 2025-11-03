"""
Generic transformer model implementation.

This module provides a generic implementation for standard transformer models
using the Hugging Face transformers library.
"""

import logging
from typing import List, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Internal dependencies
from claia.lib.data import Conversation
from claia.lib.enums.conversation import MessageRole
from ..base import LocalModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class GenericTransformerModel(LocalModel):
  """Generic transformer model implementation using Hugging Face transformers."""

  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device: str = "cpu", huggingface_api_token: Optional[str] = None, **kwargs):
    self.tokenizer = None
    self.model = None
    self.api_token = huggingface_api_token
    self.kwargs = kwargs
    super().__init__(model_name, model_path, defer_loading, device)

  def load(self) -> None:
    """Load the transformer model and tokenizer."""
    try:
      logger.info(f"Loading transformer model: {self.model_name}")

      # Load tokenizer
      self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=self.api_token)
      if self.tokenizer.pad_token is None:
        self.tokenizer.pad_token = self.tokenizer.eos_token

      # Load model
      self.model = AutoModelForCausalLM.from_pretrained(
        self.model_name,
        torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
        device_map="auto" if self.device != "cpu" else None,
        token=self.api_token
      )

      if self.device == "cpu":
        self.model = self.model.to(self.device)

      self.loaded = True
      logger.info(f"Successfully loaded transformer model: {self.model_name}")

    except Exception as e:
      logger.error(f"Error loading transformer model {self.model_name}: {e}")
      self.loaded = False
      raise

  def unload(self) -> None:
    """Unload the transformer model."""
    if self.model is not None:
      del self.model
      self.model = None
    if self.tokenizer is not None:
      del self.tokenizer
      self.tokenizer = None
    self.loaded = False
    logger.info(f"Unloaded transformer model: {self.model_name}")

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """Generate a response using the transformer model."""
    if not self.loaded:
      self.load()

    try:
      # Get settings
      settings = self.update_settings({}, conversation, **kwargs)

      # Convert conversation to prompt
      prompt = self._convert_conversation_to_prompt(conversation)

      # Tokenize input
      inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
      inputs = {k: v.to(self.device) for k, v in inputs.items()}

      # Generate response
      with torch.no_grad():
        outputs = self.model.generate(
          **inputs,
          max_new_tokens=settings.get("max_tokens", 1000),
          temperature=settings.get("temperature", 0.7),
          top_p=settings.get("top_p", 1.0),
          top_k=settings.get("top_k", 50),
          do_sample=True,
          pad_token_id=self.tokenizer.eos_token_id
        )

      # Decode response
      input_length = inputs["input_ids"].shape[1]
      generated_tokens = outputs[0][input_length:]
      response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

      # Add the response to the conversation
      conversation.add_message(MessageRole.ASSISTANT, response)

      return response

    except Exception as e:
      logger.error(f"Error generating response with transformer model {self.model_name}: {e}")
      return f"Error: {str(e)}"

  def _convert_conversation_to_prompt(self, conversation: Conversation) -> str:
    """Convert a Conversation object to a text prompt."""
    prompt_parts = []

    for message in conversation.messages:
      if message.speaker == MessageRole.SYSTEM:
        prompt_parts.append(f"System: {message.content}")
      elif message.speaker == MessageRole.USER:
        prompt_parts.append(f"User: {message.content}")
      elif message.speaker == MessageRole.ASSISTANT:
        prompt_parts.append(f"Assistant: {message.content}")

    # Add assistant prompt for generation
    prompt_parts.append("Assistant:")

    return "\n".join(prompt_parts)

  def tokenize(self, text: str) -> List[int]:
    """Tokenize the input text."""
    if not self.loaded:
      self.load()
    return self.tokenizer.encode(text)

  def detokenize(self, tokens: List[int]) -> str:
    """Convert tokens back to text."""
    if not self.loaded:
      self.load()
    return self.tokenizer.decode(tokens, skip_special_tokens=True)

  def download(self, model_path: str) -> None:
    """Download the model to the specified path."""
    try:
      logger.info(f"Downloading transformer model to: {model_path}")

      # Download tokenizer
      tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=self.api_token)
      tokenizer.save_pretrained(model_path)

      # Download model
      model = AutoModelForCausalLM.from_pretrained(self.model_name, token=self.api_token)
      model.save_pretrained(model_path)

      logger.info(f"Successfully downloaded transformer model: {self.model_name}")

    except Exception as e:
      logger.error(f"Error downloading transformer model {self.model_name}: {e}")
      raise

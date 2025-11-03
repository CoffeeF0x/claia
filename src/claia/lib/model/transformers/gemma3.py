"""
Gemma3 specialized transformer model implementation.

This module provides a specialized implementation for Gemma3 models with
custom handling for their specific requirements and optimizations.
"""

import logging
from typing import List, Optional

# Internal dependencies
from claia.lib.data import Conversation
from claia.lib.enums.conversation import MessageRole
from .generic import GenericTransformerModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class Gemma3Model(GenericTransformerModel):
  """Specialized Gemma3 transformer model implementation."""

  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device: str = "cpu", huggingface_api_token: Optional[str] = None):
    super().__init__(model_name, model_path, defer_loading, device, huggingface_api_token)

    # Gemma3-specific default settings
    self.default_settings.update({
      "max_tokens": 2048,
      "temperature": 0.8,
      "top_p": 0.95,
      "top_k": 40
    })

  def _convert_conversation_to_prompt(self, conversation: Conversation) -> str:
    """Convert a Conversation object to Gemma3-specific prompt format."""
    prompt_parts = []

    # Gemma3 uses specific formatting tokens
    for message in conversation.messages:
      if message.speaker == MessageRole.SYSTEM:
        prompt_parts.append(f"<start_of_turn>system\n{message.content}<end_of_turn>")
      elif message.speaker == MessageRole.USER:
        prompt_parts.append(f"<start_of_turn>user\n{message.content}<end_of_turn>")
      elif message.speaker == MessageRole.ASSISTANT:
        prompt_parts.append(f"<start_of_turn>model\n{message.content}<end_of_turn>")

    # Add model turn for generation
    prompt_parts.append("<start_of_turn>model\n")

    return "".join(prompt_parts)

  def load(self) -> None:
    """Load the Gemma3 model with specialized configurations."""
    try:
      logger.info(f"Loading Gemma3 model: {self.model_path}")

      # Use parent load method but with Gemma3-specific optimizations
      super().load()

      # Apply Gemma3-specific configurations
      if self.model is not None:
        # Enable gradient checkpointing for memory efficiency
        self.model.gradient_checkpointing_enable()

        # Set model to evaluation mode
        self.model.eval()

      logger.info(f"Successfully loaded Gemma3 model: {self.model_name}")

    except Exception as e:
      logger.error(f"Error loading Gemma3 model {self.model_name}: {e}")
      self.loaded = False
      raise

  def generate(self, conversation: Conversation, **kwargs) -> str:
    """Generate a response using the Gemma3 model with specialized handling."""
    if not self.loaded:
      self.load()

    try:
      # Get settings with Gemma3-specific defaults
      settings = self.update_settings({}, conversation, **kwargs)

      # Convert conversation to Gemma3 prompt format
      prompt = self._convert_conversation_to_prompt(conversation)

      # Tokenize input
      inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
      inputs = {k: v.to(self.device) for k, v in inputs.items()}

      # Generate response with Gemma3-optimized parameters
      import torch
      with torch.no_grad():
        outputs = self.model.generate(
          **inputs,
          max_new_tokens=settings.get("max_tokens", 2048),
          temperature=settings.get("temperature", 0.8),
          top_p=settings.get("top_p", 0.95),
          top_k=settings.get("top_k", 40),
          do_sample=True,
          pad_token_id=self.tokenizer.eos_token_id,
          eos_token_id=self.tokenizer.eos_token_id,
          repetition_penalty=1.1,  # Gemma3-specific
          length_penalty=1.0
        )

      # Decode response
      input_length = inputs["input_ids"].shape[1]
      generated_tokens = outputs[0][input_length:]
      response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)

      # Clean up Gemma3-specific tokens if they appear in output
      response = response.replace("<end_of_turn>", "").strip()

      return response

    except Exception as e:
      logger.error(f"Error generating response with Gemma3 model {self.model_name}: {e}")
      return f"Error: {str(e)}"

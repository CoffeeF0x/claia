"""
Gemma3 specialized transformer model implementation.

This module provides a specialized implementation for Gemma3 models with
custom handling for their specific requirements and optimizations.
"""

import logging
from typing import Any, Dict, Optional

# Internal dependencies
from ...data.models.conversation.message_sequence import MessageSequence
from ...enums.conversation import MessageRole
from .generic import GenericTransformerModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class Gemma3Model(GenericTransformerModel):
  """Specialized Gemma3 transformer model implementation.

  Generation defaults (``max_tokens``, ``temperature``, ``top_p``,
  ``top_k``) for this model live on
  ``TransformersGemma3Plugin.info.params`` as RUNTIME ``ParamSpec``
  entries; the framework resolves them into ``kwargs`` before calling
  ``generate``.
  """

  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device: str = "cpu", huggingface_api_token: Optional[str] = None):
    super().__init__(model_name, model_path, defer_loading, device, huggingface_api_token)

  def _convert_sequence_to_prompt(self, sequence: MessageSequence) -> str:
    """Convert a MessageSequence to Gemma3-specific prompt format."""
    prompt_parts = []

    if sequence.system:
      prompt_parts.append(f"<start_of_turn>system\n{sequence.system}<end_of_turn>")

    for message in sequence.messages:
      if message.speaker == MessageRole.SYSTEM:
        prompt_parts.append(f"<start_of_turn>system\n{message.content}<end_of_turn>")
      elif message.speaker == MessageRole.USER:
        prompt_parts.append(f"<start_of_turn>user\n{message.content}<end_of_turn>")
      elif message.speaker == MessageRole.ASSISTANT:
        prompt_parts.append(f"<start_of_turn>model\n{message.content}<end_of_turn>")

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

  def _get_generation_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build Gemma3-specific generation kwargs."""
    generation_kwargs = super()._get_generation_kwargs(kwargs)
    generation_kwargs.update({
      "max_new_tokens": kwargs.get("max_tokens", 128),
      "temperature": kwargs.get("temperature", 0.6),
      # "top_p": kwargs.get("top_p", 0.95),
      # "top_k": kwargs.get("top_k", 40),
      # "eos_token_id": self.tokenizer.eos_token_id,
      # "repetition_penalty": 1.1,
      # "length_penalty": 1.0,
    })
    return generation_kwargs

  def _postprocess_response(self, response: str) -> str:
    """Remove Gemma chat-template markers from the completed response."""
    return response.replace("<end_of_turn>", "").strip()

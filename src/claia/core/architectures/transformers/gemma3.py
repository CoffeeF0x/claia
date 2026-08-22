"""
Gemma3 specialized transformers architecture.

Specialized implementation for Gemma3 models with custom handling for
their prompt format, loading, and generation defaults.
"""

import logging
from typing import Any, Dict, Optional

# Internal dependencies
from ...data.models.conversation.message_sequence import MessageSequence
from ...decorators import architecture
from ...enums.conversation import MessageRole
from ...enums.plugins import ParamScope, ParamCategory
from ...plugins.base import ParamSpec
from .generic import GenericTransformerArchitecture


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
@architecture
@architecture.name("transformers_gemma3")
@architecture.title("Gemma3 Transformers Architecture")
@architecture.description("Specialized implementation for Gemma3 transformer models")
@architecture.param(ParamSpec(
  name="huggingface_api_token",
  type=str,
  scope=ParamScope.INIT,
  secret=True,
  category=ParamCategory.API,
  description="Hugging Face API Token (required for gated Gemma3 checkpoints)",
))
@architecture.param(
  ParamSpec(name="max_tokens", type=int, scope=ParamScope.RUNTIME, default=2048,
            category=ParamCategory.GENERATION,
            description="Maximum number of tokens to generate."),
  ParamSpec(name="temperature", type=float, scope=ParamScope.RUNTIME, default=0.8,
            category=ParamCategory.GENERATION,
            description="Sampling temperature."),
  ParamSpec(name="top_p", type=float, scope=ParamScope.RUNTIME, default=0.95,
            category=ParamCategory.GENERATION,
            description="Nucleus sampling probability mass."),
  ParamSpec(name="top_k", type=int, scope=ParamScope.RUNTIME, default=40,
            category=ParamCategory.GENERATION,
            description="Restrict sampling to the top-k tokens."),
)
class Gemma3Architecture(GenericTransformerArchitecture):
  """Specialized Gemma3 transformers architecture.

  Generation defaults (``max_tokens``, ``temperature``, ``top_p``,
  ``top_k``) override the inherited generic stack as RUNTIME
  ``ParamSpec`` entries; the framework resolves them into ``kwargs``
  before calling ``generate``.
  """

  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device: str = "cpu", huggingface_api_token: Optional[str] = None):
    super().__init__(model_name, model_path, defer_loading, device, huggingface_api_token)

  def _convert_sequence_to_prompt(self, sequence: MessageSequence) -> str:
    """Convert a MessageSequence to Gemma3-specific prompt format."""
    prompt_parts = []

    for message in sequence.messages:
      if message.role == MessageRole.SYSTEM:
        prompt_parts.append(f"<start_of_turn>system\n{message.content}<end_of_turn>")
      elif message.role == MessageRole.USER:
        prompt_parts.append(f"<start_of_turn>user\n{message.content}<end_of_turn>")
      elif message.role == MessageRole.ASSISTANT:
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

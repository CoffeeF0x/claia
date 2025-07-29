# External dependencies
import logging
from torch import bfloat16
from typing import Dict, Optional, Any
from transformers import AutoTokenizer, Gemma3ForCausalLM, Gemma3ForConditionalGeneration, AutoProcessor

# Internal dependencies
from .base import TransformersModel
from common.files.conversation import Conversation
from common.enums.conversation import MessageRole
from common.enums.model import ModelCapability



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class Gemma3Model(TransformersModel):
  """
  Specialized implementation for Gemma 3 models.

  This class handles all Gemma 3 specific functionality:
  - Uses the official transformers library support for Gemma 3
  - Handles text-only (TTT) and text+image (TAI/ITT) capabilities

  Usage:
    model = Gemma3Model("google/gemma-3-27b-it", capability=ModelCapability.TAI)
  """


  def __init__(
    self,
    model_name: str,
    model_path: str,
    defer_loading: bool = False,
    device: str = "cpu",
    model_params: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    capability: ModelCapability = ModelCapability.TTT):

    """
    Initialize a Gemma 3 model.

    Args:
        model_name: Model identifier
        model_path: Path to store the model
        defer_loading: Whether to defer loading
        device: Device to load on
        model_params: Additional parameters
        api_key: Hugging Face API key
        capability: Primary capability (determines text-only or vision-enabled)
    """

    # Call parent init with defer_loading=True to prevent auto-loading
    # We'll handle the loading ourselves in this class
    super().__init__(
      model_name=model_name,
      model_path=model_path,
      defer_loading=True,
      device=device,
      model_params=model_params,
      api_key=api_key,
      capability=capability
    )

    # If we're not deferring loading, explicitly call load now
    if not defer_loading:
      self.load()


  def _load_text_model(self) -> None:
    """Load a text-only Gemma 3 model."""

    logger.debug("Loading text-only Gemma 3 model")

    self.tokenizer = AutoTokenizer.from_pretrained(
      self.model_path,
      trust_remote_code=True
    )

    self.model = Gemma3ForCausalLM.from_pretrained(
      self.model_path,
      torch_dtype=bfloat16,
      device_map=self.device,
      trust_remote_code=True
    )

    logger.debug("Text-only Gemma 3 model loaded successfully")


  def _load_vision_model(self) -> None:
    """Load a Gemma 3 model with vision capabilities (for TAI/ITT)."""

    logger.debug("Loading Gemma 3 model with vision capabilities")

    self.processor = AutoProcessor.from_pretrained(
      self.model_path,
      padding_side="left",
      trust_remote_code=True
    )

    self.model = Gemma3ForConditionalGeneration.from_pretrained(
      self.model_path,
      torch_dtype=bfloat16,
      device_map=self.device,
      trust_remote_code=True
    )

    # For compatibility with token counting, etc.
    self.tokenizer = self.processor.tokenizer

    logger.debug("Gemma 3 model with vision capabilities loaded successfully")


  def _generate_impl(self, conversation: Conversation, **kwargs) -> str:

    """
    Implement generation for Gemma 3 models.

    This method handles both text-only and vision-enabled Gemma 3 models,
    selecting the appropriate processing approach based on the model's
    configuration.

    Args:
        conversation: The Conversation object containing messages
        **kwargs: Generation parameters

    Returns:
        str: The generated text response
    """

    logger.info("Generating response with Gemma 3 model")

    formatted_messages = []

    # Add system prompt if available
    if conversation.prompt:
      if self.capability in [ModelCapability.TAI, ModelCapability.ITT]:
        # Vision-enabled models expect content as array of typed objects
        formatted_messages.append({
          "role": "system",
          "content": [{"type": "text", "text": conversation.prompt}]
        })
      else:
        # Text-only models expect content as string
        formatted_messages.append({
          "role": "system",
          "content": conversation.prompt
        })

    # Get user and assistant messages
    conversation_messages = conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT])

    # Convert to format expected by the model
    for message in conversation_messages:
      if self.capability in [ModelCapability.TAI, ModelCapability.ITT]:
        # Vision-enabled models expect content as array of typed objects
        formatted_messages.append({
          "role": message.speaker.value,
          "content": [{"type": "text", "text": message.content}]
        })
      else:
        # Text-only models expect content as string
        formatted_messages.append({
          "role": message.speaker.value,
          "content": message.content
        })

    logger.debug(f"Formatted {len(formatted_messages)} messages for generation")

    # Use appropriate generation approach based on capability
    if self.capability in [ModelCapability.TAI, ModelCapability.ITT] and hasattr(self, 'processor'):
      logger.debug(f"Using vision-enabled generation for capability {self.capability.value}")

      # Convert messages to inputs using the processor
      inputs = self.processor.apply_chat_template(
        formatted_messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True
        # do_pan_and_scan=kwargs.get('high_res', False)
      ).to(self.device)

      # Generate the output
      output = self.model.generate(
        **inputs,
        max_new_tokens=kwargs.get('max_new_tokens', 8192),
        top_p=kwargs.get('top_p', 0.7),
        temperature=kwargs.get('temperature', 0.7)
      )

      # Decode only the new tokens
      response = self.processor.decode(output[0], skip_special_tokens=True)[inputs.input_ids.shape[1]:]
    else:
      logger.debug("Using text-only generation")

      # For text-only, use the standard tokenizer flow
      model_inputs = self.tokenizer.apply_chat_template(
        formatted_messages,
        return_tensors="pt",
        add_generation_prompt=True
      ).to(self.device)

      model_outputs = self.model.generate(
        model_inputs,
        max_new_tokens=kwargs.get('max_new_tokens', 8192),
        top_p=kwargs.get('top_p', 0.7),
        temperature=kwargs.get('temperature', 0.7)
      )

      output_token_ids = model_outputs[0][len(model_inputs[0]):]
      response = self.tokenizer.decode(output_token_ids, skip_special_tokens=True)

    # Add the response as an assistant message to the conversation
    conversation.add_message(MessageRole.ASSISTANT, response)

    logger.info("Response generated successfully")
    logger.debug(f"Generated response: {response[:100]}...")
    return response


  def _download_text_model(self, model_path: str) -> None:
    """Download a text-only Gemma 3 model."""

    logger.debug("Downloading text-only Gemma 3 model")

    # Download and save model
    Gemma3ForCausalLM.from_pretrained(
      self.model_name,
      torch_dtype=bfloat16,
      trust_remote_code=True,
      **self.model_params.get('model', {})
    ).save_pretrained(model_path)

    # Download and save tokenizer
    AutoTokenizer.from_pretrained(
      self.model_name,
      trust_remote_code=True,
      **self.model_params.get('tokenizer', {})
    ).save_pretrained(model_path)

    logger.debug("Text-only Gemma 3 model downloaded successfully")


  def _download_vision_model(self, model_path: str) -> None:
    """Download a Gemma 3 model with vision capabilities (for TAI/ITT)."""

    logger.debug("Downloading Gemma 3 model with vision capabilities")

    # Download and save model
    Gemma3ForConditionalGeneration.from_pretrained(
      self.model_name,
      torch_dtype=bfloat16,
      trust_remote_code=True,
      **self.model_params.get('model', {})
    ).save_pretrained(model_path)

    # Download and save processor
    AutoProcessor.from_pretrained(
      self.model_name,
      padding_side="left",
      trust_remote_code=True,
      **self.model_params.get('processor', {})
    ).save_pretrained(model_path)

    logger.debug("Gemma 3 model with vision capabilities downloaded successfully")
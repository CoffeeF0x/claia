# External dependencies
import os
from torch import bfloat16
from torch.cuda import empty_cache
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, logging as transformers_logging
from typing import List, Dict, Optional, Union, Any, Callable, Type
from huggingface_hub import login

# Internal dependencies
from ..base import LocalModel, APIModel
# from settings import Settings
from common.files.conversation import Conversation
from common.enums.conversation import MessageRole
from common.enums.model import ModelCapability



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                          DEFAULT SETTINGS                            #
########################################################################
# Default generation settings for models
# Individual models can override specific settings as needed
DEFAULT_SETTINGS = {
  "max_new_tokens": 4096,
  "top_p": 0.7,
  "temperature": 0.7
}



########################################################################
#                               CLASSES                                #
########################################################################
class TransformersModel(LocalModel):
  """
  Unified base class for transformer models using Hugging Face libraries.

  This class handles common operations for all transformer models:
  - Authentication and API key management
  - Model checking, downloading, and loading
  - Default implementations for various capabilities
  - Conversation-based generation
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
    Initialize a transformer model.

    Args:
        model_name: The model identifier (HuggingFace repo ID)
        model_path: Base path where models are stored
        defer_loading: Whether to defer loading the model
        device: Device to load the model on
        model_params: Additional parameters for the model
        api_key: Hugging Face API key for authentication
        capability: Primary capability of this model
    """

    self.model_params = model_params or {}
    self.api_key = api_key
    self.capability = capability

    # Determine full model path
    folder_name = model_name.split("/")[-1]
    full_model_path = os.path.join(model_path, folder_name)

    logger.debug(f"Initializing TransformersModel for {model_name} with path {full_model_path}")
    logger.debug(f"Model capability: {capability.value}")

    if api_key:
      masked_key = f"{api_key[:5]}{'*' * (len(api_key) - 5)}" if len(api_key) > 5 else "***"
      logger.debug(f"API key provided (first 5 chars: {api_key[:5]})")
    else:
      logger.debug("No API key provided")

    # Initialize base class
    super().__init__(model_name, full_model_path, defer_loading, device)

    # Initialize model components as None
    self.tokenizer = None
    self.processor = None
    self.model = None

    # Load immediately if not deferring
    if not defer_loading:
      self.load()


  def _authenticate_huggingface(self) -> None:
    """Authenticate with Hugging Face using the API token."""

    if self.api_key:
      logger.info("Authenticating with Hugging Face")
      logger.debug(f"Using API key (first 5 chars: {self.api_key[:5]})")
      login(token=self.api_key)
      logger.info("Successfully authenticated with Hugging Face")
    else:
      logger.warning("No Hugging Face API token provided. Some models may not be accessible.")


  def set_api_key(self, api_key: str) -> None:
    """Set the API key for Hugging Face authentication."""

    logger.debug(f"Setting API key (first 5 chars: {api_key[:5]})")
    self.api_key = api_key


  def load(self) -> None:

    """
    Load the model based on its capability.

    This method checks if the model exists locally, downloads it if needed,
    and loads the appropriate model class based on the capability.
    """

    logger.debug(f"Loading model {self.model_name} with capability {self.capability.value}")

    # Check if model exists locally, download if needed
    if not os.path.exists(self.model_path):
      logger.debug(f"Model path {self.model_path} does not exist, downloading model")
      self._authenticate_huggingface()
      self.download(self.model_path)
    else:
      logger.debug(f"Model path {self.model_path} exists, loading from disk")

    # Load appropriate model components based on capability
    try:
      if self.capability == ModelCapability.TTT:
        self._load_text_model()
      elif self.capability in [ModelCapability.TTI, ModelCapability.DEFAULT]:
        self._load_image_model()
      elif self.capability in [ModelCapability.TAI, ModelCapability.ITT]:
        self._load_vision_model()
      else:
        logger.warning(f"Unsupported capability: {self.capability.value}, falling back to text model")
        self._load_text_model()

      self.loaded = True
      logger.info(f"Model {self.model_name} loaded successfully")
    except Exception as e:
      logger.error(f"Error loading model: {str(e)}")
      raise


  def _load_text_model(self) -> None:
    """Load a text-to-text model."""

    logger.debug("Loading text-to-text model")
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
    self.model = AutoModelForCausalLM.from_pretrained(
      self.model_path,
      torch_dtype=bfloat16,
      device_map=self.device,
      trust_remote_code=True
    )
    logger.debug("Text model loaded successfully")


  def _load_image_model(self) -> None:

    """
    Load a text-to-image model.

    Override this in subclasses with specific image generation implementation.
    """

    logger.debug("Loading text-to-image model")
    # This is a placeholder - specific implementations should override this
    logger.warning("Default text-to-image loading not implemented, subclasses should override")
    self._load_text_model()  # Fallback to text model


  def _load_vision_model(self) -> None:

    """
    Load a vision-enabled model.

    Override this in subclasses with specific vision implementation.
    """

    logger.debug("Loading vision-enabled model")
    # This is a placeholder - specific implementations should override this
    logger.warning("Default vision model loading not implemented, subclasses should override")
    self._load_text_model()  # Fallback to text model


  def reset_context(self) -> None:
    """Reset the context (history) for the model if applicable."""
    # Implementation for context reset if needed
    pass


  def unload(self) -> None:
    """Unload the model and free memory."""

    logging.info(f"Unloading model {self.model_name}")
    self.model = None
    self.tokenizer = None
    self.processor = None
    empty_cache()
    self.loaded = False
    logging.info("Model unloaded successfully")

  def tokenize(self, text: str) -> List[int]:
    """Tokenize text using the model's tokenizer."""
    if not self.tokenizer:
      raise RuntimeError("Tokenizer not loaded")

    logging.debug(f"Tokenizing text: {text[:50]}...")
    return self.tokenizer.encode(text)

  def detokenize(self, tokens: List[int]) -> str:
    """Detokenize tokens using the model's tokenizer."""
    if not self.tokenizer:
      raise RuntimeError("Tokenizer not loaded")

    logging.debug(f"Detokenizing tokens")
    return self.tokenizer.decode(tokens, skip_special_tokens=True)


  def generate(self, conversation: Conversation, **kwargs) -> Any:

    """
    Generate output based on the model's capability and the conversation.

    This is the main entry point for all generation requests. It handles
    common pre-processing and post-processing, delegating the actual generation
    to the _generate_impl method which can be overridden by subclasses.

    Args:
        conversation: The Conversation object containing messages
        **kwargs: Additional generation parameters

    Returns:
        Generated output (text, image, etc. depending on capability)
    """

    if not self.is_loaded():
      self.load()

    logging.info(f"Generating with {self.capability.value} model")

    # Apply model-specific generation settings
    generation_params = self.model_params.get('generation', {}).copy()
    generation_params.update(kwargs)

    # Delegate to the implementation method
    response = self._generate_impl(conversation, **generation_params)

    # Don't add the response to the conversation if it's already been added
    # by the implementation method
    return response


  def _generate_impl(self, conversation: Conversation, **kwargs) -> Any:

    """
    Implementation of the generation logic.

    This is the method that subclasses should override to provide
    specialized generation behavior. The default implementation handles
    text-to-text generation.

    Args:
        conversation: The Conversation object containing messages
        **kwargs: Generation parameters (already merged with model defaults)

    Returns:
        Generated output (specific type depends on implementation)
    """

    logging.info("Generating text response")

    # Format messages from the conversation
    formatted_messages = []

    # Add system prompt if available
    if conversation.prompt:
      formatted_messages.append({
        "role": "system",
        "content": conversation.prompt
      })

    # Get user and assistant messages
    conversation_messages = conversation.get_messages([MessageRole.USER, MessageRole.ASSISTANT])

    # Convert to format expected by tokenizer
    for message in conversation_messages:
      formatted_messages.append({
        "role": message.speaker.value,
        "content": message.content
      })

    logging.debug(f"Input messages: {len(formatted_messages)}")

    # Generate the response
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
    response = self.detokenize(output_token_ids)

    # Add the response as an assistant message to the conversation
    conversation.add_message(MessageRole.ASSISTANT, response)

    logging.info("Response generated successfully")
    logging.debug(f"Generated response: {response[:100]}...")
    return response


  def download(self, model_path: str) -> None:

    """
    Download the model from HuggingFace.

    Args:
        model_path: Path to save the model
    """

    logger.info(f"Downloading {self.model_name} model to {model_path}")
    os.makedirs(model_path, exist_ok=True)

    # Ensure we're authenticated with Hugging Face
    self._authenticate_huggingface()

    try:
      # Download and save appropriate components based on capability
      if self.capability == ModelCapability.TTT:
        self._download_text_model(model_path)
      elif self.capability == ModelCapability.TTI:
        self._download_image_model(model_path)
      elif self.capability in [ModelCapability.TAI, ModelCapability.ITT]:
        self._download_vision_model(model_path)
      else:
        logger.warning(f"Unsupported capability: {self.capability.value}, falling back to text model download")
        self._download_text_model(model_path)

      logger.info("Model downloaded successfully")
    except Exception as e:
      logger.error(f"Error downloading model: {str(e)}")
      raise


  def _download_text_model(self, model_path: str) -> None:
    """Download a text-to-text model."""

    logger.debug(f"Downloading text model weights for {self.model_name}")

    # Download and save model
    AutoModelForCausalLM.from_pretrained(
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

    logger.debug("Text model downloaded successfully")


  def _download_image_model(self, model_path: str) -> None:

    """
    Download a text-to-image model.

    Override this in subclasses with specific implementation.
    """

    logger.warning("Default text-to-image download not implemented, subclasses should override")
    self._download_text_model(model_path)  # Fallback to text model


  def _download_vision_model(self, model_path: str) -> None:

    """
    Download a vision-enabled model.

    Override this in subclasses with specific implementation.
    """

    logger.warning("Default vision model download not implemented, subclasses should override")
    self._download_text_model(model_path)  # Fallback to text model
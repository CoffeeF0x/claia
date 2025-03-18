# External dependencies
import os
from torch import bfloat16
from torch.cuda import empty_cache
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, logging as transformers_logging
from typing import List, Dict, Optional, Union, Any, Callable
from huggingface_hub import login

# Internal dependencies
from models.base import LocalModel, APIModel
from settings import Settings



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
class TransformersLocalModel(LocalModel):
  def __init__(self,
               model_name: str,
               model_path: str,
               defer_loading: bool = False,
               device: str = "cpu",
               model_params: Optional[Dict[str, Any]] = None,
               api_key: Optional[str] = None):
    self.model_params = model_params or {}
    self.api_key = api_key
    folder_name = model_name.split("/")[-1]
    full_model_path = os.path.join(model_path, folder_name)
    logger.debug(f"Initializing TransformersLocalModel for {model_name} with path {full_model_path}")
    if api_key:
      masked_key = f"{api_key[:5]}{'*' * (len(api_key) - 5)}" if len(api_key) > 5 else "***"
      logger.debug(f"API key provided (first 5 chars: {api_key[:5]})")
    else:
      logger.debug("No API key provided")
    super().__init__(model_name, full_model_path, defer_loading, device)

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
    logger.debug(f"Loading model {self.model_name}")
    if not os.path.exists(self.model_path):
      logger.debug(f"Model path {self.model_path} does not exist, downloading model")
      self._authenticate_huggingface()
      self.download(self.model_path)
    else:
      logger.debug(f"Model path {self.model_path} exists, loading from disk")

    logger.info(f"Loading model from {self.model_path}")
    try:
      logger.debug("Loading tokenizer")
      self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
      logger.debug("Loading model")
      self.model = AutoModelForCausalLM.from_pretrained(
        self.model_path,
        torch_dtype=bfloat16,
        device_map=self.device,
        trust_remote_code=True
      )
      self.loaded = True
      logger.info("Model loaded successfully")
    except Exception as e:
      logger.error(f"Error loading model: {str(e)}")
      raise

  def reset_context(self) -> None:
    # Implementation for context reset if needed
    pass

  def unload(self) -> None:
    logging.info("Unloading model")
    self.model = None
    self.tokenizer = None
    empty_cache()
    self.loaded = False
    logging.info("Model unloaded successfully")

  def tokenize(self, text: str) -> List[int]:
    logging.debug(f"Tokenizing text: {text}")
    return self.tokenizer.encode(text)

  def detokenize(self, tokens: List[int]) -> str:
    logging.debug(f"Detokenizing tokens: {tokens}")
    return self.tokenizer.decode(tokens, skip_special_tokens=True)

  def generate(self, messages: list, **kwargs) -> str:
    if not self.is_loaded():
      self.load()

    logging.info("Generating response")
    logging.debug(f"Input messages: {messages}")
    logging.debug(f"Generation parameters: {kwargs}")

    # Apply model-specific generation settings
    generation_params = self.model_params.get('generation', {}).copy()
    generation_params.update(kwargs)

    model_inputs = self.tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(self.device)

    model_outputs = self.model.generate(
      model_inputs,
      max_new_tokens=generation_params.get('max_new_tokens', 8192),
      top_p=generation_params.get('top_p', 0.7),
      temperature=generation_params.get('temperature', 0.7)
    )

    output_token_ids = model_outputs[0][len(model_inputs[0]):]
    response = self.detokenize(output_token_ids)
    logging.info("Response generated successfully")
    logging.debug(f"Generated response: {response}")
    return response

  def download(self, model_path: str) -> None:
    logger.info(f"Downloading {self.model_name} model to {model_path}")
    os.makedirs(model_path, exist_ok=True)

    # Ensure we're authenticated with Hugging Face
    self._authenticate_huggingface()

    try:
      # Download and save model
      logger.debug(f"Downloading model weights for {self.model_name}")
      AutoModelForCausalLM.from_pretrained(
        self.model_name,
        torch_dtype=bfloat16,
        trust_remote_code=True,
        **self.model_params.get('model', {})
      ).save_pretrained(model_path)
      logger.debug("Model weights downloaded successfully")

      # Download and save tokenizer
      logger.debug(f"Downloading tokenizer for {self.model_name}")
      AutoTokenizer.from_pretrained(
        self.model_name,
        trust_remote_code=True,
        **self.model_params.get('tokenizer', {})
      ).save_pretrained(model_path)
      logger.debug("Tokenizer downloaded successfully")

      logger.info("Model downloaded successfully")
    except Exception as e:
      logger.error(f"Error downloading model: {str(e)}")
      raise



########################################################################
#                       TRANSFORMERS MODEL                             #
########################################################################
class TransformersModel(LocalModel):
  """
  A class-based implementation of the transformers source.

  This class follows the pattern of other model source classes like OpenAIModel,
  but creates local transformer models based on HuggingFace model IDs.
  """

  def __init__(self, model_id: str, model_path: str = "models", defer_loading: bool = False, device: str = "cpu", api_key: Optional[str] = None):
    """
    Initialize a transformers text model.

    Args:
        model_id: The model identifier (also used as HF repo ID)
        model_path: Base path where models are stored
        defer_loading: Whether to defer loading the model
        device: Device to load the model on
        api_key: Hugging Face API key for authentication
    """
    # Initialize essential attributes first to avoid reference errors
    self.model_instance = None
    self.model_path = model_path
    self.defer_loading = defer_loading
    self.device = device
    self.loaded = False
    self.api_key = api_key

    logger.debug(f"Initializing TransformersModel for {model_id}")
    if api_key:
      logger.debug(f"API key provided (first 5 chars: {api_key[:5]})")
    else:
      logger.debug("No API key provided")

    # Set model parameters with default settings
    self.model_params = {
      'model': {},
      'tokenizer': {},
      'generation': DEFAULT_SETTINGS.copy()
    }
    logger.debug(f"Model parameters: {self.model_params}")

    # Call super to initialize the base class
    super().__init__(model_name=model_id, model_path=model_path, defer_loading=defer_loading, device=device)

    # Create the actual model instance for delegation
    folder_name = self.model_name.split("/")[-1]
    self.full_model_path = os.path.join(model_path, folder_name)
    logger.debug(f"Full model path: {self.full_model_path}")

    # Only create the instance if not deferring loading
    if not defer_loading:
      logger.debug("Not deferring loading, creating model instance")
      self._create_model_instance()
    else:
      logger.debug("Deferring loading, model instance will be created later")

  def set_api_key(self, api_key: str) -> None:
    """Set the API key for Hugging Face authentication."""
    logger.debug(f"Setting API key in TransformersModel (first 5 chars: {api_key[:5]})")
    self.api_key = api_key
    if hasattr(self, 'model_instance') and self.model_instance is not None:
      logger.debug("Propagating API key to model instance")
      self.model_instance.set_api_key(api_key)
    else:
      logger.debug("No model instance to propagate API key to")

  def _create_model_instance(self) -> None:
    """Create the underlying model instance."""
    try:
      logger.info(f"Creating TransformersLocalModel instance for {self.model_name}")
      self.model_instance = TransformersLocalModel(
        model_name=self.model_name,
        model_path=self.model_path,
        defer_loading=self.defer_loading,
        device=self.device,
        model_params=self.model_params,
        api_key=self.api_key
      )
      logger.info(f"Successfully created model instance for {self.model_name}")
    except Exception as e:
      logger.error(f"Error creating model instance for {self.model_name}: {str(e)}")
      raise ValueError(f"Failed to create model instance: {str(e)}")

  def load(self) -> None:
    """Load the model."""
    logger.debug(f"Loading model {self.model_name}")
    if not hasattr(self, 'model_instance') or self.model_instance is None:
      logger.debug("No model instance, creating one")
      self._create_model_instance()
    logger.debug("Loading model instance")
    self.model_instance.load()
    self.loaded = True
    logger.debug("Model loaded successfully")

  def is_loaded(self) -> bool:
    """Check if the model is loaded."""
    if not hasattr(self, 'model_instance') or self.model_instance is None:
      return False
    return self.model_instance.is_loaded()

  def unload(self) -> None:
    """Unload the model."""
    if hasattr(self, 'model_instance') and self.model_instance is not None:
      self.model_instance.unload()
    self.loaded = False

  def reset_context(self) -> None:
    """Reset the model context."""
    if hasattr(self, 'model_instance') and self.model_instance is not None:
      self.model_instance.reset_context()

  def generate(self, messages: list, **kwargs) -> str:
    """Generate a response to the given messages."""
    if not hasattr(self, 'model_instance') or self.model_instance is None:
      self._create_model_instance()
    return self.model_instance.generate(messages, **kwargs)

  def download(self, model_path: str) -> None:
    """Download the model."""
    if not hasattr(self, 'model_instance') or self.model_instance is None:
      self._create_model_instance()
    self.model_instance.download(model_path)

  def tokenize(self, text: str) -> List[int]:
    """Tokenize the text."""
    if not hasattr(self, 'model_instance') or self.model_instance is None:
      self._create_model_instance()
    return self.model_instance.tokenize(text)

  def detokenize(self, tokens: List[int]) -> str:
    """Detokenize the tokens."""
    if not hasattr(self, 'model_instance') or self.model_instance is None:
      self._create_model_instance()
    return self.model_instance.detokenize(tokens)
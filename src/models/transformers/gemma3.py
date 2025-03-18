# External dependencies
import os
import logging
from torch import bfloat16
from torch.cuda import empty_cache
from typing import List, Dict, Optional, Union, Any

# Internal dependencies
from models.transformers.base import TransformersModel, TransformersLocalModel, DEFAULT_SETTINGS



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class Gemma3LocalModel(TransformersLocalModel):
  """
  Specialized implementation for Gemma 3 models.
  Handles both text-only and multimodal capabilities.
  """

  def __init__(self,
               model_name: str,
               model_path: str,
               defer_loading: bool = False,
               device: str = "cpu",
               model_params: Optional[Dict[str, Any]] = None,
               api_key: Optional[str] = None,
               multimodal: bool = True):
    """
    Initialize a Gemma 3 model.

    Args:
        model_name: Model identifier
        model_path: Path to store the model
        defer_loading: Whether to defer loading
        device: Device to load on
        model_params: Additional parameters
        api_key: Hugging Face API key
        multimodal: Whether to load multimodal capabilities
    """
    self.multimodal = multimodal

    # Explicitly call parent init with defer_loading=True to prevent auto-loading
    # We'll handle the loading ourselves in this class
    super().__init__(model_name, model_path, True, device, model_params, api_key)

    # If we're not deferring loading, explicitly call load now
    if not defer_loading:
      self.load()

  def load(self) -> None:
    """Load the appropriate Gemma 3 model class based on multimodal setting."""
    if not os.path.exists(self.model_path):
      self._authenticate_huggingface()
      self.download(self.model_path)

    logger.info(f"Loading Gemma 3 model from {self.model_path}")

    try:
      # Import appropriate classes based on multimodal setting
      if self.multimodal:
        logger.debug("Loading multimodal Gemma 3 model")
        from transformers import AutoProcessor, Gemma3ForConditionalGeneration
        self.processor = AutoProcessor.from_pretrained(self.model_path, padding_side="left", trust_remote_code=True)
        self.model = Gemma3ForConditionalGeneration.from_pretrained(
          self.model_path,
          torch_dtype=bfloat16,
          device_map=self.device,
          trust_remote_code=True
        )
      else:
        logger.debug("Loading text-only Gemma 3 model")
        from transformers import AutoTokenizer, Gemma3ForCausalLM
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
        self.model = Gemma3ForCausalLM.from_pretrained(
          self.model_path,
          torch_dtype=bfloat16,
          device_map=self.device,
          trust_remote_code=True
        )

      self.loaded = True
      logger.info("Gemma 3 model loaded successfully")
    except Exception as e:
      logger.error(f"Error loading Gemma 3 model: {str(e)}")
      raise

  def generate(self, messages: list, **kwargs) -> str:
    """Generate a response for Gemma 3 model.

    Handles both text-only and multimodal inputs appropriately.
    """
    if not self.is_loaded():
      self.load()

    logger.info("Generating response with Gemma 3")

    # Apply model-specific generation settings
    generation_params = self.model_params.get('generation', {}).copy()
    generation_params.update(kwargs)

    # Check if it's multimodal
    if self.multimodal:
      logger.debug("Using multimodal generation")

      # Convert messages to inputs using the processor
      inputs = self.processor.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
        do_pan_and_scan=generation_params.get('high_res', False)
      ).to(self.device)

      # Generate the output
      output = self.model.generate(
        **inputs,
        max_new_tokens=generation_params.get('max_new_tokens', 8192),
        top_p=generation_params.get('top_p', 0.7),
        temperature=generation_params.get('temperature', 0.7)
      )

      # Decode only the new tokens
      response = self.processor.decode(output[0], skip_special_tokens=True)[inputs.input_ids.shape[1]:]
    else:
      logger.debug("Using text-only generation")

      # For text-only, use the standard tokenizer flow
      model_inputs = self.tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True).to(self.device)

      model_outputs = self.model.generate(
        model_inputs,
        max_new_tokens=generation_params.get('max_new_tokens', 8192),
        top_p=generation_params.get('top_p', 0.7),
        temperature=generation_params.get('temperature', 0.7)
      )

      output_token_ids = model_outputs[0][len(model_inputs[0]):]
      response = self.tokenizer.decode(output_token_ids, skip_special_tokens=True)

    logger.info("Response generated successfully")
    logger.debug(f"Generated response: {response}")
    return response

  def download(self, model_path: str) -> None:
    """Download the appropriate Gemma 3 model based on multimodal setting."""
    logger.info(f"Downloading Gemma 3 model {self.model_name} to {model_path}")
    os.makedirs(model_path, exist_ok=True)

    # Ensure we're authenticated with Hugging Face
    self._authenticate_huggingface()

    try:
      if self.multimodal:
        logger.debug("Downloading multimodal Gemma 3 model")
        from transformers import AutoProcessor, Gemma3ForConditionalGeneration

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
      else:
        logger.debug("Downloading text-only Gemma 3 model")
        from transformers import AutoTokenizer, Gemma3ForCausalLM

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

      logger.info("Gemma 3 model downloaded successfully")
    except Exception as e:
      logger.error(f"Error downloading Gemma 3 model: {str(e)}")
      raise



########################################################################
#                         GEMMA 3 MODEL                                #
########################################################################
class Gemma3Model(TransformersModel):
  """
  Specialized implementation for Gemma 3 models.
  """

  def __init__(self, model_id: str, model_path: str = "models", defer_loading: bool = False,
               device: str = "cpu", api_key: Optional[str] = None):
    """
    Initialize a Gemma 3 model.

    Args:
        model_id: The model identifier (also used as HF repo ID)
        model_path: Base path where models are stored
        defer_loading: Whether to defer loading the model
        device: Device to load the model on
        api_key: Hugging Face API key for authentication
    """
    # Determine if multimodal based on model ID (1B is text-only)
    self.multimodal = "1b" not in model_id.lower()
    logger.debug(f"Initializing Gemma 3 model for {model_id}")
    logger.debug(f"Multimodal: {self.multimodal}")

    # Initialize essential attributes
    self.model_instance = None
    self.model_path = model_path
    self.defer_loading = defer_loading
    self.device = device
    self.loaded = False
    self.api_key = api_key

    # Set model parameters with default settings
    self.model_params = {
      'model': {},
      'tokenizer': {},
      'processor': {},
      'generation': DEFAULT_SETTINGS.copy()
    }

    # Call super to initialize the base class
    super().__init__(model_id=model_id, model_path=model_path, defer_loading=True, device=device, api_key=api_key)

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
    logger.debug(f"Setting API key in Gemma3Model (first 5 chars: {api_key[:5]})")
    self.api_key = api_key
    if hasattr(self, 'model_instance') and self.model_instance is not None:
      logger.debug("Propagating API key to model instance")
      self.model_instance.set_api_key(api_key)

  def load(self) -> None:
    """Load the model if not already loaded."""
    if self.is_loaded():
      logger.debug(f"Model {self.model_name} is already loaded, skipping")
      return

    logger.debug(f"Loading model {self.model_name}")
    if not hasattr(self, 'model_instance') or self.model_instance is None:
      logger.debug("No model instance, creating one")
      self._create_model_instance()
    else:
      logger.debug("Model instance exists, loading it")
      self.model_instance.load()

    self.loaded = True
    logger.debug("Model loaded successfully")

  def is_loaded(self) -> bool:
    """Check if the model is loaded."""
    # First check our own loaded flag
    if self.loaded:
      return True

    # Then check if we have a model instance and if it's loaded
    if hasattr(self, 'model_instance') and self.model_instance is not None:
      return self.model_instance.is_loaded()

    return False

  def _create_model_instance(self) -> None:
    """Create the underlying model instance."""
    try:
      logger.info(f"Creating Gemma3LocalModel instance for {self.model_name}")
      self.model_instance = Gemma3LocalModel(
        model_name=self.model_name,
        model_path=self.model_path,
        defer_loading=self.defer_loading,
        device=self.device,
        model_params=self.model_params,
        api_key=self.api_key,
        multimodal=self.multimodal
      )
      logger.info(f"Successfully created model instance for {self.model_name}")
    except Exception as e:
      logger.error(f"Error creating model instance for {self.model_name}: {str(e)}")
      raise ValueError(f"Failed to create model instance: {str(e)}")
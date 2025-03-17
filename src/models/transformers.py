# External dependencies
import os
from torch import bfloat16
from torch.cuda import empty_cache
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, logging as transformers_logging
from typing import List, Dict, Optional, Union, Any, Callable

# Internal dependencies
from models.base import LocalModel, APIModel



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class TransformersLocalModel(LocalModel):
  def __init__(self,
               model_name: str,
               model_path: str,
               hf_repo_id: str,
               defer_loading: bool = False,
               device: str = "cpu",
               model_params: Optional[Dict[str, Any]] = None):
    self.hf_repo_id = hf_repo_id
    self.model_params = model_params or {}
    folder_name = self.hf_repo_id.split("/")[-1]
    full_model_path = os.path.join(model_path, folder_name)
    super().__init__(model_name, full_model_path, defer_loading, device)

  def load(self) -> None:
    if not os.path.exists(self.model_path):
      self.download(self.model_path)

    logging.info(f"Loading model from {self.model_path}")
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
    self.model = AutoModelForCausalLM.from_pretrained(
      self.model_path,
      torch_dtype=bfloat16,
      device_map=self.device,
      trust_remote_code=True
    )
    self.loaded = True
    logging.info("Model loaded successfully")

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
    logging.info(f"Downloading {self.hf_repo_id} model to {model_path}")
    os.makedirs(model_path, exist_ok=True)

    # Download and save model
    AutoModelForCausalLM.from_pretrained(
      self.hf_repo_id,
      torch_dtype=bfloat16,
      trust_remote_code=True,
      **self.model_params.get('model', {})
    ).save_pretrained(model_path)

    # Download and save tokenizer
    AutoTokenizer.from_pretrained(
      self.hf_repo_id,
      trust_remote_code=True,
      **self.model_params.get('tokenizer', {})
    ).save_pretrained(model_path)

    logging.info("Model downloaded successfully")



########################################################################
#                       TRANSFORMERS TEXT MODEL                        #
########################################################################
class TransformersTextModel(LocalModel):
  """
  A class-based implementation of the transformers source.

  This class follows the pattern of other model source classes like OpenAITextModel,
  but creates local transformer models based on the model's configuration in the
  definitions file.
  """

  def __init__(self, model_id: str, model_path: str = "models", defer_loading: bool = False, device: str = "cpu"):
    """
    Initialize a transformers text model.

    Args:
        model_id: The model identifier from definitions
        model_path: Base path where models are stored
        defer_loading: Whether to defer loading the model
        device: Device to load the model on
    """
    # Import here to avoid circular imports
    from models.definitions import definitions, DEFAULT_SETTINGS

    # We need to use model_id directly from the definitions since LocalModel expects model_name
    super().__init__(model_name=model_id, model_path=model_path, defer_loading=defer_loading, device=device)

    # Get the model configuration
    self.model_config = definitions.get(model_id, {})
    if not self.model_config:
      raise ValueError(f"Model {model_id} not found in definitions")

    # Get the HuggingFace repo ID
    self.hf_repo_id = self._get_hf_repo_id()

    # Get model settings, applying defaults and overrides
    model_specific_settings = self.model_config.get('settings', {})
    merged_settings = DEFAULT_SETTINGS.copy()
    merged_settings.update(model_specific_settings)

    # Set model parameters
    self.model_params = {
      'model': {},
      'tokenizer': {},
      'generation': merged_settings
    }

    # Create the actual model instance for delegation
    folder_name = self.hf_repo_id.split("/")[-1]
    self.full_model_path = os.path.join(model_path, folder_name)
    self.model_instance = None

    # Only create the instance if not deferring loading
    if not defer_loading:
      self._create_model_instance()

  def _get_hf_repo_id(self) -> str:
    """Get the HuggingFace repo ID from the model configuration."""
    # Check if there's a direct transformers source in the config
    transformers_source = self.model_config.get('sources', {}).get('transformers')
    if transformers_source:
      if isinstance(transformers_source, list) and transformers_source:
        return transformers_source[0]
      return transformers_source

    # Fall back to looking for a vllm source, which typically contains HF repo IDs
    vllm_source = self.model_config.get('sources', {}).get('vllm')
    if vllm_source and isinstance(vllm_source, list) and vllm_source:
      return vllm_source[0]

    raise ValueError(f"Could not determine HF repo ID for model {self.model_name}")

  def _create_model_instance(self) -> None:
    """Create the underlying model instance."""
    if not self.model_instance:
      self.model_instance = TransformersLocalModel(
        model_name=self.model_name,
        model_path=self.model_path,
        hf_repo_id=self.hf_repo_id,
        defer_loading=self.defer_loading,
        device=self.device,
        model_params=self.model_params
      )

  def load(self) -> None:
    """Load the model."""
    if not self.model_instance:
      self._create_model_instance()
    self.model_instance.load()
    self.loaded = True

  def is_loaded(self) -> bool:
    """Check if the model is loaded."""
    return self.model_instance and self.model_instance.is_loaded() if self.model_instance else False

  def unload(self) -> None:
    """Unload the model."""
    if self.model_instance:
      self.model_instance.unload()
    self.loaded = False

  def reset_context(self) -> None:
    """Reset the model context."""
    if self.model_instance:
      self.model_instance.reset_context()

  def generate(self, messages: list, **kwargs) -> str:
    """Generate a response to the given messages."""
    if not self.model_instance:
      self._create_model_instance()
    return self.model_instance.generate(messages, **kwargs)

  def download(self, model_path: str) -> None:
    """Download the model."""
    if not self.model_instance:
      self._create_model_instance()
    self.model_instance.download(model_path)

  def tokenize(self, text: str) -> List[int]:
    """Tokenize the text."""
    if not self.model_instance:
      self._create_model_instance()
    return self.model_instance.tokenize(text)

  def detokenize(self, tokens: List[int]) -> str:
    """Detokenize the tokens."""
    if not self.model_instance:
      self._create_model_instance()
    return self.model_instance.detokenize(tokens)

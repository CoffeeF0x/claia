# External dependencies
import os
import logging
import torch
from typing import List, Dict, Optional, Union, Any
from PIL import Image
from diffusers import StableDiffusionPipeline, DiffusionPipeline, EulerDiscreteScheduler, DPMSolverMultistepScheduler

# Internal dependencies
from .base import TransformersLocalModel, TransformersModel, DEFAULT_SETTINGS



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class DiffusionLocalModel(TransformersLocalModel):
  """
  Specialized implementation for diffusion-based image generation models.
  Handles text-to-image generation including Stable Diffusion variants.
  """

  def __init__(self,
               model_name: str,
               model_path: str,
               defer_loading: bool = False,
               device: str = "cpu",
               model_params: Optional[Dict[str, Any]] = None,
               api_key: Optional[str] = None):
    """
    Initialize a diffusion model.

    Args:
        model_name: Model identifier (HuggingFace repo ID)
        model_path: Path to store the model
        defer_loading: Whether to defer loading
        device: Device to load on
        model_params: Additional parameters
        api_key: Hugging Face API key
    """
    # Set default image generation parameters
    self.default_image_params = {
      "height": 512,
      "width": 512,
      "num_inference_steps": 50,
      "guidance_scale": 7.5,
      "negative_prompt": None,
      "guidance_rescale": 0.7
    }

    # Explicitly call parent init
    super().__init__(model_name, model_path, True, device, model_params, api_key)

    # If we're not deferring loading, explicitly call load now
    if not defer_loading:
      self.load()

  def load(self) -> None:
    """Load the appropriate diffusion model."""
    if not os.path.exists(self.model_path):
      logger.debug(f"Model path {self.model_path} does not exist, downloading model")
      self._authenticate_huggingface()
      self.download(self.model_path)
    else:
      logger.debug(f"Model path {self.model_path} exists, loading from disk")

    logger.info(f"Loading diffusion model from {self.model_path}")

    try:
      # Load the appropriate pipeline based on model type
      # By default use StableDiffusionPipeline for text-to-image
      torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
      device_map = self.device

      # Determine scheduler type from model_params if specified
      pipeline_type = self.model_params.get('pipeline_type', 'text2img')
      scheduler_type = self.model_params.get('scheduler', 'euler')

      logger.debug(f"Using pipeline type: {pipeline_type}")
      logger.debug(f"Using scheduler type: {scheduler_type}")

      # Initialize the appropriate scheduler
      if scheduler_type.lower() == 'euler':
        scheduler = EulerDiscreteScheduler.from_pretrained(
          self.model_path,
          subfolder="scheduler"
        )
        logger.debug("Using EulerDiscreteScheduler")
      elif scheduler_type.lower() == 'dpm':
        scheduler = DPMSolverMultistepScheduler.from_pretrained(
          self.model_path,
          subfolder="scheduler"
        )
        logger.debug("Using DPMSolverMultistepScheduler")
      else:
        scheduler = None
        logger.debug("Using default scheduler")

      # Load the appropriate pipeline
      if pipeline_type == 'text2img':
        if scheduler:
          self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.model_path,
            scheduler=scheduler,
            torch_dtype=torch_dtype,
            use_safetensors=True,
            device_map=device_map
          )
        else:
          self.pipeline = StableDiffusionPipeline.from_pretrained(
            self.model_path,
            torch_dtype=torch_dtype,
            use_safetensors=True,
            device_map=device_map
          )
      else:
        # For other pipeline types, use the generic DiffusionPipeline
        # which will automatically instantiate the correct pipeline
        if scheduler:
          self.pipeline = DiffusionPipeline.from_pretrained(
            self.model_path,
            scheduler=scheduler,
            torch_dtype=torch_dtype,
            use_safetensors=True,
            device_map=device_map
          )
        else:
          self.pipeline = DiffusionPipeline.from_pretrained(
            self.model_path,
            torch_dtype=torch_dtype,
            use_safetensors=True,
            device_map=device_map
          )

      # Enable memory optimization if on GPU
      if torch.cuda.is_available():
        # Enable attention slicing for memory efficiency
        self.pipeline.enable_attention_slicing()

        # Enable xformers memory efficient attention if available
        try:
          if 'xformers' in self.model_params.get('optimizations', []):
            logger.debug("Enabling xformers memory efficient attention")
            self.pipeline.enable_xformers_memory_efficient_attention()
        except Exception as e:
          logger.warning(f"Could not enable xformers: {str(e)}")

      self.loaded = True
      logger.info("Diffusion model loaded successfully")
    except Exception as e:
      logger.error(f"Error loading diffusion model: {str(e)}")
      raise

  def generate_image(self, prompt: str, **kwargs) -> Image.Image:
    """
    Generate an image from a text prompt.

    Args:
        prompt: Text prompt to generate image from
        **kwargs: Additional generation parameters

    Returns:
        Generated PIL Image
    """
    if not self.is_loaded():
      self.load()

    logger.info(f"Generating image with prompt: '{prompt[:50]}...' (truncated)")

    # Combine default parameters with model parameters and user parameters
    generation_params = self.default_image_params.copy()
    model_gen_params = self.model_params.get('generation', {})
    generation_params.update(model_gen_params)
    generation_params.update(kwargs)

    logger.debug(f"Generation parameters: {generation_params}")

    # Extract parameters for the pipeline
    height = generation_params.pop("height", 512)
    width = generation_params.pop("width", 512)
    num_inference_steps = generation_params.pop("num_inference_steps", 50)
    guidance_scale = generation_params.pop("guidance_scale", 7.5)
    negative_prompt = generation_params.pop("negative_prompt", None)
    guidance_rescale = generation_params.pop("guidance_rescale", 0.7)

    # Generate the image
    try:
      output = self.pipeline(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        negative_prompt=negative_prompt,
        guidance_rescale=guidance_rescale,
        **generation_params
      )

      # Get the image from the output
      image = output.images[0]

      logger.info("Image generated successfully")
      return image
    except Exception as e:
      logger.error(f"Error generating image: {str(e)}")
      raise

  def download(self, model_path: str) -> None:
    """
    Download the diffusion model.

    Args:
        model_path: Path to download the model to
    """
    logger.info(f"Downloading diffusion model {self.model_name} to {model_path}")
    os.makedirs(model_path, exist_ok=True)

    # Ensure we're authenticated with Hugging Face
    self._authenticate_huggingface()

    try:
      # Use pipeline to download model - it will handle the appropriate components
      # and save them to the specified path
      pipeline_type = self.model_params.get('pipeline_type', 'text2img')
      scheduler_type = self.model_params.get('scheduler', 'euler')

      # Determine if we need a custom scheduler
      if scheduler_type.lower() == 'euler':
        scheduler = EulerDiscreteScheduler.from_config(
          StableDiffusionPipeline.from_pretrained(
            self.model_name,
            use_auth_token=self.api_key,
            subfolder="scheduler"
          ).scheduler.config
        )
      elif scheduler_type.lower() == 'dpm':
        scheduler = DPMSolverMultistepScheduler.from_config(
          StableDiffusionPipeline.from_pretrained(
            self.model_name,
            use_auth_token=self.api_key,
            subfolder="scheduler"
          ).scheduler.config
        )
      else:
        scheduler = None

      if pipeline_type == 'text2img':
        if scheduler:
          StableDiffusionPipeline.from_pretrained(
            self.model_name,
            scheduler=scheduler,
            use_safetensors=True,
            **self.model_params.get('model', {})
          ).save_pretrained(model_path)
        else:
          StableDiffusionPipeline.from_pretrained(
            self.model_name,
            use_safetensors=True,
            **self.model_params.get('model', {})
          ).save_pretrained(model_path)
      else:
        if scheduler:
          DiffusionPipeline.from_pretrained(
            self.model_name,
            scheduler=scheduler,
            use_safetensors=True,
            **self.model_params.get('model', {})
          ).save_pretrained(model_path)
        else:
          DiffusionPipeline.from_pretrained(
            self.model_name,
            use_safetensors=True,
            **self.model_params.get('model', {})
          ).save_pretrained(model_path)

      logger.info("Diffusion model downloaded successfully")
    except Exception as e:
      logger.error(f"Error downloading diffusion model: {str(e)}")
      raise



########################################################################
#                        DIFFUSION MODEL                               #
########################################################################
class DiffusionModel(TransformersModel):
  """
  Specialized implementation for diffusion-based image generation models.
  """

  def __init__(self, model_id: str, model_path: str = "models", defer_loading: bool = False,
               device: str = "cpu", api_key: Optional[str] = None):
    """
    Initialize a diffusion model.

    Args:
        model_id: The model identifier (also used as HF repo ID)
        model_path: Base path where models are stored
        defer_loading: Whether to defer loading the model
        device: Device to load the model on
        api_key: Hugging Face API key for authentication
    """
    # Initialize essential attributes
    self.model_instance = None
    self.model_path = model_path
    self.defer_loading = defer_loading
    self.device = device
    self.loaded = False
    self.api_key = api_key

    logger.debug(f"Initializing DiffusionModel for {model_id}")
    if api_key:
      logger.debug(f"API key provided (first 5 chars: {api_key[:5]})")
    else:
      logger.debug("No API key provided")

    # Set model parameters with default settings
    # Default to the Euler scheduler which is recommended for most use cases
    self.model_params = {
      'model': {},
      'scheduler': 'euler',
      'optimizations': ['attention_slicing'],
      'generation': {
        'height': 512,
        'width': 512,
        'num_inference_steps': 50,
        'guidance_scale': 7.5,
        'guidance_rescale': 0.7
      }
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

  def _create_model_instance(self) -> None:
    """Create the underlying diffusion model instance."""
    try:
      logger.info(f"Creating DiffusionLocalModel instance for {self.model_name}")
      self.model_instance = DiffusionLocalModel(
        model_name=self.model_name,
        model_path=self.full_model_path,
        defer_loading=self.defer_loading,
        device=self.device,
        model_params=self.model_params,
        api_key=self.api_key
      )
      logger.info(f"Successfully created model instance for {self.model_name}")
    except Exception as e:
      logger.error(f"Error creating model instance for {self.model_name}: {str(e)}")
      raise ValueError(f"Failed to create model instance: {str(e)}")

  def generate_image(self, prompt: str, **kwargs) -> Image.Image:
    """
    Generate an image from a text prompt.

    Args:
        prompt: Text prompt to generate image from
        **kwargs: Additional generation parameters

    Returns:
        Generated PIL Image
    """
    if not self.is_loaded():
      self.load()

    return self.model_instance.generate_image(prompt, **kwargs)
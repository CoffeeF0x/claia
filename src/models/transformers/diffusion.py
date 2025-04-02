# External dependencies
import os
import io
import logging
import torch
from typing import Dict, Optional, Any
from PIL import Image
from diffusers import StableDiffusionPipeline

# Internal dependencies
from .base import TransformersModel
from files import Conversation, ImageFile
from enums import MessageRole, ModelCapability



########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               CLASSES                                #
########################################################################
class DiffusionModel(TransformersModel):
  """
  Simple diffusion model for image generation using Stable Diffusion.

  This class handles text-to-image generation and attaches the resulting
  images to conversation messages.
  """

  def __init__(self,
               model_name: str,
               model_path: str = "models",
               defer_loading: bool = False,
               device: str = "cuda" if torch.cuda.is_available() else "cpu",
               model_params: Optional[Dict[str, Any]] = None,
               api_key: Optional[str] = None):
    """
    Initialize a diffusion model.

    Args:
        model_name: Model identifier (HuggingFace repo ID)
        model_path: Path to store the model
        defer_loading: Whether to defer loading until generation
        device: Device to load the model on (defaults to CUDA if available)
        model_params: Additional parameters for the model
        api_key: Hugging Face API key for authentication
    """
    # Set default image generation parameters
    self.default_image_params = {
      "height": 512,
      "width": 512,
      "num_inference_steps": 30,
      "guidance_scale": 7.5,
      "negative_prompt": None
    }

    # Initialize the pipeline to None
    self.pipeline = None

    # Call parent init with the TTI capability
    super().__init__(
      model_name=model_name,
      model_path=model_path,
      defer_loading=defer_loading,
      device=device,
      model_params=model_params,
      api_key=api_key,
      capability=ModelCapability.TTI
    )

  def _load_image_model(self) -> None:
    """Load a text-to-image diffusion model."""
    logger.debug(f"Loading diffusion model from {self.model_path}")

    # Use float16 precision on GPU, float32 on CPU
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    # Load the stable diffusion pipeline
    self.pipeline = StableDiffusionPipeline.from_pretrained(
      self.model_path,
      torch_dtype=torch_dtype,
      use_safetensors=True,
      device_map=self.device
    )

    # Enable memory optimizations on GPU
    if torch.cuda.is_available():
      self.pipeline.enable_attention_slicing()
      try:
        self.pipeline.enable_xformers_memory_efficient_attention()
        logger.debug("Enabled xformers memory efficient attention")
      except Exception as e:
        logger.debug(f"Could not enable xformers: {str(e)}")

    logger.debug("Diffusion model loaded successfully")

  def _generate_impl(self, conversation: Conversation, **kwargs) -> str:
    """
    Generate an image based on the conversation and attach it to a message.

    Args:
        conversation: The conversation object containing the message history
        **kwargs: Additional generation parameters

    Returns:
        str: A message indicating the image was generated
    """
    # Ensure the model is loaded
    if not self.is_loaded():
      self.load()

    logger.info("Generating image from conversation")

    # Get the last user message as the prompt
    user_messages = conversation.get_messages(MessageRole.USER)

    if not user_messages:
      error_msg = "No user messages found in conversation"
      logger.warning(error_msg)
      conversation.add_message(MessageRole.ASSISTANT,
                              f"Error: {error_msg}. Please provide a prompt.")
      return f"Error: {error_msg}"

    # Use the most recent user message as the prompt
    prompt = user_messages[-1].content
    logger.debug(f"Using prompt: '{prompt[:50]}...' (truncated)")

    # Combine parameters
    generation_params = self.default_image_params.copy()
    model_gen_params = self.model_params.get('generation', {})
    generation_params.update(model_gen_params)
    generation_params.update(kwargs)

    # Extract parameters for the pipeline
    height = generation_params.pop("height", 512)
    width = generation_params.pop("width", 512)
    num_inference_steps = generation_params.pop("num_inference_steps", 30)
    guidance_scale = generation_params.pop("guidance_scale", 7.5)
    negative_prompt = generation_params.pop("negative_prompt", None)

    # Generate the image
    try:
      output = self.pipeline(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        negative_prompt=negative_prompt,
        **generation_params
      )

      # Get the first image from the output
      image = output.images[0]

      # Convert PIL image to bytes
      image_bytes = io.BytesIO()
      image.save(image_bytes, format="PNG")
      image_bytes.seek(0)

      # Create an image file from the bytes
      file_name = f"generated_image_{len(user_messages)}.png"
      image_file = self._save_image_to_file(image_bytes.getvalue(),
                                         conversation.base_directory,
                                         file_name)

      # Create a response message
      response = f"Generated image from prompt: '{prompt[:100]}...' (truncated)"
      message = conversation.add_message(MessageRole.ASSISTANT, response)

      # Attach the image to the message
      if image_file and message:
        conversation.attach_file(message.message_id, image_file.file_id)
        logger.info(f"Attached image {image_file.file_id} to message {message.message_id}")

      return response

    except Exception as e:
      error_message = f"Error generating image: {str(e)}"
      logger.error(error_message)
      conversation.add_message(MessageRole.ASSISTANT, error_message)
      return error_message

  def _save_image_to_file(self, image_data: bytes, base_directory: str,
                         file_name: str) -> Optional[ImageFile]:
    """
    Save image data to a file and return the ImageFile object.

    Args:
        image_data: Binary image data
        base_directory: Base directory for file storage
        file_name: Name for the file

    Returns:
        Optional[ImageFile]: The created ImageFile, or None if creation failed
    """
    try:
      # Create an ImageFile from the bytes
      image_file = ImageFile.from_bytes(
        image_data=image_data,
        base_directory=base_directory,
        file_name=file_name,
        format="png",
        mime_type="image/png",
        metadata={"source": "diffusion_model", "model": self.model_name}
      )

      logger.debug(f"Created image file: {image_file.file_id}")
      return image_file

    except Exception as e:
      logger.error(f"Failed to create image file: {str(e)}")
      return None

  def _download_image_model(self, model_path: str) -> None:
    """Download a stable diffusion model."""
    logger.info(f"Downloading {self.model_name} model to {model_path}")

    # Load and immediately save the model to the specified path
    StableDiffusionPipeline.from_pretrained(
      self.model_name,
      torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
      use_safetensors=True,
      **self.model_params.get('model', {})
    ).save_pretrained(model_path)

    logger.info("Model downloaded successfully")
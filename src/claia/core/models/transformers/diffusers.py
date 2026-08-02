"""
Generic local Diffusers model implementation.

This module hosts image-generation models backed by Hugging Face
``diffusers`` pipelines. The Claia boundary stays generic: a text prompt
goes in, typed image byte chunks come out.
"""

import io
import logging
from typing import Any, Dict, Generator, List, Optional

import torch
from diffusers import DiffusionPipeline

from claia.core.data.chunks import BaseChunk, ImageChunk, TextChunk
from claia.core.data.models.conversation.message_sequence import MessageSequence
from claia.core.data.response import ModelResponse
from claia.core.enums.data import ImageFormat
from ..base import LocalModel


logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_FORMAT = "PNG"
SUPPORTED_OUTPUT_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}

PIPELINE_PROFILES: Dict[str, Dict[str, Any]] = {
  "default": {
    "param_aliases": {
      "num_images": "num_images_per_prompt",
    },
    "unsupported_params": set(),
  },
  "stable-diffusion": {
    "param_aliases": {
      "num_images": "num_images_per_prompt",
    },
    "unsupported_params": set(),
  },
}


class DiffusersModel(LocalModel):
  """Generic local image model backed by a Diffusers pipeline."""

  def __init__(
    self,
    model_name: str,
    model_path: Optional[str] = None,
    defer_loading: bool = False,
    device: str = "cpu",
    huggingface_api_token: Optional[str] = None,
    pipeline_profile: Optional[str] = None,
    **kwargs,
  ):
    self.pipeline = None
    self.api_token = huggingface_api_token
    self.pipeline_profile = pipeline_profile or self._infer_pipeline_profile(model_name)
    self.kwargs = kwargs
    super().__init__(model_name, model_path, defer_loading, device)

  def load(self) -> None:
    """Load the Diffusers pipeline."""
    try:
      logger.info(f"Loading diffusers pipeline: {self.model_name}")
      dtype = torch.float16 if self.device != "cpu" else torch.float32

      self.pipeline = DiffusionPipeline.from_pretrained(
        self.model_path or self.model_name,
        torch_dtype=dtype,
        token=self.api_token,
        **self.kwargs,
      )
      self.pipeline = self.pipeline.to(self.device)

      if self.device == "cuda" and getattr(torch.cuda, "is_available", lambda: False)():
        self._enable_cuda_memory_optimizations()

      self.loaded = True
      logger.info(f"Successfully loaded diffusers pipeline: {self.model_name}")

    except Exception as e:
      logger.error(f"Error loading diffusers pipeline {self.model_name}: {e}")
      self.loaded = False
      raise

  def unload(self) -> None:
    """Unload the pipeline."""
    if self.pipeline is not None:
      del self.pipeline
      self.pipeline = None
    self.loaded = False
    logger.info(f"Unloaded diffusers pipeline: {self.model_name}")

  def generate(
    self,
    sequence: MessageSequence,
    **kwargs,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate one or more images from the latest user prompt."""
    chunks: list = []
    if not self.loaded:
      self.load()

    try:
      prompt = self._resolve_prompt(sequence, kwargs.get("prompt"))
      pipeline_kwargs = self._build_pipeline_kwargs(prompt, kwargs)

      output = self.pipeline(**pipeline_kwargs)
      images = list(getattr(output, "images", []) or [])
      if not images:
        message = TextChunk(data="No images were returned by the diffusers pipeline.")
        chunks.append(message)
        yield message
        return ModelResponse(chunks=chunks, complete=False, error=message.data)

      summary = TextChunk(
        data=f"Generated {len(images)} image{'s' if len(images) != 1 else ''}."
      )
      chunks.append(summary)
      yield summary

      output_format = self._normalize_output_format(kwargs.get("output_format"))
      media_type = SUPPORTED_OUTPUT_FORMATS[output_format]
      try:
        image_fmt = ImageFormat(output_format.lower())
      except ValueError:
        image_fmt = ImageFormat.PNG
      for index, image in enumerate(images):
        image_bytes = self._image_to_bytes(image, output_format)
        image_chunk = ImageChunk(
          data=image_bytes,
          format=image_fmt,
          metadata={
            "media_type": media_type,
            "format": output_format,
            "index": index,
            "model": self.model_name,
            "prompt": prompt,
            "seed": kwargs.get("seed"),
            "width": getattr(image, "width", None),
            "height": getattr(image, "height", None),
          },
        )
        chunks.append(image_chunk)
        yield image_chunk

      return ModelResponse(chunks=chunks, complete=True, metadata={"text": summary.data})

    except Exception as e:
      logger.error(f"Error generating image with diffusers model {self.model_name}: {e}")
      chunk = TextChunk(data=f"Error: {str(e)}")
      chunks.append(chunk)
      yield chunk
      return ModelResponse(chunks=chunks, complete=False, error=str(e))

  def tokenize(self, text: str) -> List[int]:
    """Tokenization is not exposed for image pipelines."""
    raise NotImplementedError("DiffusersModel does not expose tokenization.")

  def detokenize(self, tokens: List[int]) -> str:
    """Detokenization is not exposed for image pipelines."""
    raise NotImplementedError("DiffusersModel does not expose detokenization.")

  def download(self, model_path: str) -> None:
    """Download and save the pipeline to ``model_path``."""
    logger.info(f"Downloading diffusers pipeline {self.model_name} to {model_path}")
    pipeline = DiffusionPipeline.from_pretrained(
      self.model_name,
      token=self.api_token,
      **self.kwargs,
    )
    pipeline.save_pretrained(model_path)

  def _enable_cuda_memory_optimizations(self) -> None:
    """Enable optional CUDA memory optimizations when the pipeline supports them."""
    if hasattr(self.pipeline, "enable_attention_slicing"):
      self.pipeline.enable_attention_slicing()
    if hasattr(self.pipeline, "enable_xformers_memory_efficient_attention"):
      try:
        self.pipeline.enable_xformers_memory_efficient_attention()
      except Exception as e:
        logger.debug(f"Could not enable xformers memory efficient attention: {e}")

  def _resolve_prompt(self, sequence: MessageSequence, prompt_override: Optional[str]) -> str:
    """Resolve the prompt from explicit kwargs or the latest user message."""
    if prompt_override:
      return prompt_override

    text = sequence.latest_user_text()
    if not text:
      raise ValueError("No user prompt found for image generation.")
    return text

  def _build_pipeline_kwargs(self, prompt: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Translate Claia runtime kwargs into Diffusers pipeline kwargs."""
    profile = PIPELINE_PROFILES.get(self.pipeline_profile, PIPELINE_PROFILES["default"])
    aliases = profile.get("param_aliases", {})
    unsupported = profile.get("unsupported_params", set())

    pipeline_kwargs: Dict[str, Any] = {"prompt": prompt}
    for name in (
      "negative_prompt",
      "height",
      "width",
      "num_inference_steps",
      "guidance_scale",
      "num_images",
    ):
      if name in unsupported:
        continue
      value = kwargs.get(name)
      if value is None:
        continue
      pipeline_kwargs[aliases.get(name, name)] = value

    seed = kwargs.get("seed")
    if seed is not None:
      pipeline_kwargs["generator"] = self._build_generator(seed)

    return pipeline_kwargs

  def _build_generator(self, seed: int) -> Any:
    """Build a torch generator for deterministic image generation."""
    try:
      generator = torch.Generator(device=self.device)
    except TypeError:
      generator = torch.Generator()
    return generator.manual_seed(seed)

  def _image_to_bytes(self, image: Any, output_format: str) -> bytes:
    """Serialize a PIL-like image object to bytes."""
    if output_format == "JPEG" and getattr(image, "mode", None) in {"RGBA", "LA", "P"}:
      image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format=output_format)
    return buffer.getvalue()

  def _normalize_output_format(self, output_format: Optional[str]) -> str:
    """Normalize and validate image output format."""
    normalized = (output_format or DEFAULT_OUTPUT_FORMAT).upper()
    if normalized == "JPG":
      normalized = "JPEG"
    if normalized not in SUPPORTED_OUTPUT_FORMATS:
      raise ValueError(
        f"Unsupported output_format '{output_format}'. "
        f"Expected one of {sorted(SUPPORTED_OUTPUT_FORMATS)}."
      )
    return normalized

  def _infer_pipeline_profile(self, model_name: str) -> str:
    """Infer a broad profile from the provider model id."""
    lowered = model_name.lower()
    if "stable-diffusion" in lowered or "stable_diffusion" in lowered:
      return "stable-diffusion"
    return "default"

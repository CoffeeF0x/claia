"""
Generic transformer model implementation.

This module provides a generic implementation for standard transformer models
using the Hugging Face transformers library.
"""

import logging
from queue import Empty
from threading import Thread
from typing import Any, Dict, List, Optional, Generator, Sequence
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import torch

# Internal dependencies
from claia.core.data import Conversation
from claia.core.data.artifacts import BaseArtifact
from claia.core.data.chunks import BaseChunk, TextChunk
from claia.core.data.response import ModelResponse
from claia.core.enums.conversation import MessageRole
from ..base import LocalModel


########################################################################
#                            INITIALIZATION                            #
########################################################################
logger = logging.getLogger(__name__)


########################################################################
#                               CLASSES                                #
########################################################################
class GenericTransformerModel(LocalModel):
  """Generic transformer model implementation using Hugging Face transformers."""

  def __init__(self, model_name: str, model_path: str, defer_loading: bool = False, device: str = "cpu", huggingface_api_token: Optional[str] = None, **kwargs):
    self.tokenizer = None
    self.model = None
    self.api_token = huggingface_api_token
    self.kwargs = kwargs
    super().__init__(model_name, model_path, defer_loading, device)

  def load(self) -> None:
    """Load the transformer model and tokenizer."""
    try:
      logger.info(f"Loading transformer model: {self.model_name}")

      # Load tokenizer
      self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=self.api_token)
      if self.tokenizer.pad_token is None:
        self.tokenizer.pad_token = self.tokenizer.eos_token

      # Load model
      self.model = AutoModelForCausalLM.from_pretrained(
        self.model_name,
        torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
        device_map="auto" if self.device != "cpu" else None,
        token=self.api_token
      )

      if self.device == "cpu":
        self.model = self.model.to(self.device)

      self.loaded = True
      logger.info(f"Successfully loaded transformer model: {self.model_name}")

    except Exception as e:
      logger.error(f"Error loading transformer model {self.model_name}: {e}")
      self.loaded = False
      raise

  def unload(self) -> None:
    """Unload the transformer model."""
    if self.model is not None:
      del self.model
      self.model = None
    if self.tokenizer is not None:
      del self.tokenizer
      self.tokenizer = None
    self.loaded = False
    logger.info(f"Unloaded transformer model: {self.model_name}")

  def generate(
    self,
    artifacts: Sequence[BaseArtifact],
    **kwargs,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate a response using the transformer model."""
    conversation = Conversation.from_artifacts(artifacts)
    chunks: list = []
    if not self.loaded:
      self.load()

    try:
      prompt = self._convert_conversation_to_prompt(conversation)
      inputs = self._tokenize_prompt(prompt)

      if kwargs.get("stream", False):
        token_gen = self._generate_streaming(inputs, kwargs)
        try:
          while True:
            token = next(token_gen)
            chunk = TextChunk(data=token) if isinstance(token, str) else token
            chunks.append(chunk)
            yield chunk
        except StopIteration as stop:
          return ModelResponse(
            chunks=chunks,
            complete=True,
            metadata={"text": stop.value},
          )
      else:
        response = self._generate_blocking(inputs, kwargs)
        chunk = TextChunk(data=response)
        chunks.append(chunk)
        yield chunk
        return ModelResponse(chunks=chunks, complete=True, metadata={"text": response})

    except Exception as e:
      logger.error(f"Error generating response with transformer model {self.model_name}: {e}")
      chunk = TextChunk(data=f"Error: {str(e)}")
      chunks.append(chunk)
      yield chunk
      return ModelResponse(chunks=chunks, complete=False, error=str(e))

  def _tokenize_prompt(self, prompt: str) -> Dict[str, Any]:
    """Tokenize and move a prompt to the configured device."""
    inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)
    return {k: v.to(self.device) for k, v in inputs.items()}

  def _get_generation_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Build Hugging Face generation kwargs from resolved runtime params."""
    generation_kwargs = {
      "max_new_tokens": kwargs.get("max_tokens", 1000),
      "temperature": kwargs.get("temperature", 0.7),
      "top_p": kwargs.get("top_p", 1.0),
      "do_sample": True,
      "pad_token_id": self.tokenizer.eos_token_id,
    }

    top_k = kwargs.get("top_k")
    if top_k is not None:
      generation_kwargs["top_k"] = top_k

    return generation_kwargs

  def _generate_blocking(self, inputs: Dict[str, Any], kwargs: Dict[str, Any]) -> str:
    """Generate the complete response before yielding it."""
    with torch.no_grad():
      outputs = self.model.generate(
        **inputs,
        **self._get_generation_kwargs(kwargs),
      )

    input_length = inputs["input_ids"].shape[1]
    generated_tokens = outputs[0][input_length:]
    response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
    return self._postprocess_response(response)

  def _generate_streaming(self, inputs: Dict[str, Any], kwargs: Dict[str, Any]) -> Generator[str, None, str]:
    """Generate text in a background thread and yield decoded deltas."""
    streamer = TextIteratorStreamer(
      self.tokenizer,
      skip_prompt=True,
      skip_special_tokens=True,
      timeout=0.5,
    )
    generation_kwargs = {
      **inputs,
      **self._get_generation_kwargs(kwargs),
      "streamer": streamer,
    }
    errors = []

    def run_generation() -> None:
      try:
        with torch.no_grad():
          self.model.generate(**generation_kwargs)
      except Exception as e:
        errors.append(e)
        # Unblock the iterator if generation fails before transformers
        # has a chance to signal the stream end.
        streamer.on_finalized_text("", stream_end=True)

    thread = Thread(target=run_generation, daemon=True)
    thread.start()

    full_response = ""
    stream_finished = False
    while thread.is_alive() and not stream_finished:
      try:
        chunk = next(streamer)
      except Empty:
        continue
      except StopIteration:
        stream_finished = True
        break
      if chunk:
        text = self._postprocess_stream_chunk(chunk)
        full_response += text
        yield text

    if not stream_finished:
      for chunk in streamer:
        if chunk:
          text = self._postprocess_stream_chunk(chunk)
          full_response += text
          yield text

    thread.join()

    if errors:
      raise errors[0]

    return self._postprocess_response(full_response)

  def _postprocess_stream_chunk(self, chunk: str) -> str:
    """Post-process one streamed text delta."""
    return chunk

  def _postprocess_response(self, response: str) -> str:
    """Post-process the complete model response."""
    return response.strip()

  def _convert_conversation_to_prompt(self, conversation: Conversation) -> str:
    """Convert a Conversation object to a text prompt."""
    prompt_parts = []

    for message in conversation.get_thread():
      if message.speaker == MessageRole.SYSTEM:
        prompt_parts.append(f"System: {message.content}")
      elif message.speaker == MessageRole.USER:
        prompt_parts.append(f"User: {message.content}")
      elif message.speaker == MessageRole.ASSISTANT:
        prompt_parts.append(f"Assistant: {message.content}")

    # Add assistant prompt for generation
    prompt_parts.append("Assistant:")

    return "\n".join(prompt_parts)

  def tokenize(self, text: str) -> List[int]:
    """Tokenize the input text."""
    if not self.loaded:
      self.load()
    return self.tokenizer.encode(text)

  def detokenize(self, tokens: List[int]) -> str:
    """Convert tokens back to text."""
    if not self.loaded:
      self.load()
    return self.tokenizer.decode(tokens, skip_special_tokens=True)

  def download(self, model_path: str) -> None:
    """Download the model to the specified path."""
    try:
      logger.info(f"Downloading transformer model to: {model_path}")

      # Download tokenizer
      tokenizer = AutoTokenizer.from_pretrained(self.model_name, token=self.api_token)
      tokenizer.save_pretrained(model_path)

      # Download model
      model = AutoModelForCausalLM.from_pretrained(self.model_name, token=self.api_token)
      model.save_pretrained(model_path)

      logger.info(f"Successfully downloaded transformer model: {self.model_name}")

    except Exception as e:
      logger.error(f"Error downloading transformer model {self.model_name}: {e}")
      raise

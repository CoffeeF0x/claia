"""
Generic local text-to-speech model implementation.

The public Claia boundary is capability-oriented: text goes in and
``AUDIO_BYTES`` chunks come out. Model-specific runtimes are isolated in
small backend adapters.
"""

import io
import importlib
import logging
from typing import Any, Dict, Generator, List, Optional, Tuple

from ...data.artifacts import BaseArtifact, TextArtifact
from ...data.chunks import AudioChunk, BaseChunk, TextChunk
from ...data.request import AgentRequest, ModelInputs
from ...data.response import ModelResponse
from ...decorators import architecture
from ...enums.data import AudioFormat
from ...enums.plugins import ParamScope, ParamCategory
from ...plugins.base import ParamSpec
from ..base import LocalArchitecture


logger = logging.getLogger(__name__)

MEDIA_TYPES = {
  "wav": "audio/wav",
}


@architecture
@architecture.name("tts")
@architecture.title("Text-to-Speech Architecture")
@architecture.description("Generic local text-to-speech generation")
@architecture.param(ParamSpec(
  name="huggingface_api_token",
  type=str,
  scope=ParamScope.INIT,
  secret=True,
  category=ParamCategory.API,
  description="Hugging Face API Token (required for gated audio models).",
))
@architecture.param(ParamSpec(
  name="model_path",
  type=str,
  scope=ParamScope.INIT,
  default=None,
  category=ParamCategory.DIRECTORY,
  description="Optional local path for loading a downloaded TTS model.",
))
@architecture.param(ParamSpec(
  name="device",
  type=str,
  scope=ParamScope.INIT,
  default="cpu",
  category=ParamCategory.MODEL,
  description="Device used to run the model, such as cpu, cuda, or cuda:0.",
))
@architecture.param(ParamSpec(
  name="defer_loading",
  type=bool,
  scope=ParamScope.INIT,
  default=False,
  category=ParamCategory.MODEL,
  description="Defer model loading until the first generation call.",
))
@architecture.param(ParamSpec(
  name="dtype",
  type=str,
  scope=ParamScope.INIT,
  default="auto",
  choices=["auto", "float32", "float16", "bfloat16"],
  category=ParamCategory.MODEL,
  description="Model dtype for local inference.",
))
@architecture.param(ParamSpec(
  name="tts_backend",
  type=str,
  scope=ParamScope.INIT,
  default="qwen3_tts",
  choices=["qwen3_tts"],
  category=ParamCategory.MODEL,
  description="Local TTS backend adapter.",
))
@architecture.param(ParamSpec(
  name="prompt",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=ParamCategory.PROMPT,
  description="Optional text override. Defaults to the latest user message.",
))
@architecture.param(ParamSpec(
  name="language",
  type=str,
  scope=ParamScope.RUNTIME,
  default="English",
  category=ParamCategory.GENERATION,
  description="Language label passed to the TTS backend.",
))
@architecture.param(ParamSpec(
  name="voice",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=ParamCategory.GENERATION,
  description="Optional voice or voice preset when supported by a backend.",
))
@architecture.param(ParamSpec(
  name="reference_audio_path",
  type=str,
  scope=ParamScope.RUNTIME,
  default=None,
  category=ParamCategory.GENERATION,
  description="Reference audio path for voice cloning. Required by Qwen3-TTS Base.",
))
@architecture.param(ParamSpec(
  name="response_format",
  type=str,
  scope=ParamScope.RUNTIME,
  default="wav",
  choices=["wav"],
  category=ParamCategory.GENERATION,
  description="Encoded audio output format.",
))
@architecture.param(ParamSpec(
  name="sample_rate",
  type=int,
  scope=ParamScope.RUNTIME,
  default=None,
  category=ParamCategory.GENERATION,
  description="Optional requested output sample rate.",
))
class TTSArchitecture(LocalArchitecture):
  """Generic local TTS architecture that delegates to a backend adapter."""

  def __init__(
    self,
    model_name: str,
    model_path: Optional[str] = None,
    defer_loading: bool = False,
    device: str = "cpu",
    huggingface_api_token: Optional[str] = None,
    dtype: str = "auto",
    tts_backend: str = "qwen3_tts",
    **kwargs,
  ):
    self.model_name = model_name
    self.model_path = model_path
    self.device = device
    self.api_token = huggingface_api_token
    self.dtype = dtype
    self.tts_backend = tts_backend
    self.kwargs = kwargs
    self.backend = self._create_backend(tts_backend)
    super().__init__(model_name, model_path, defer_loading, device)

  def load(self) -> None:
    """Load the configured TTS backend."""
    try:
      logger.info(f"Loading local TTS backend '{self.tts_backend}' for {self.model_name}")
      self.backend.load()
      self.loaded = True
    except Exception as e:
      logger.error(f"Error loading TTS model {self.model_name}: {e}")
      self.loaded = False
      raise

  def unload(self) -> None:
    """Unload the backend model."""
    self.backend.unload()
    self.loaded = False

  def generate(
    self,
    request: AgentRequest,
  ) -> Generator[BaseChunk, None, ModelResponse]:
    """Generate speech audio from text artifact input or a prompt override."""
    chunks: list = []
    if not self.loaded:
      self.load()

    inputs = request.inputs
    args = request.args
    text = self._resolve_text(inputs, args.get("prompt") or args.get("input"))
    response_format = self._normalize_response_format(args.get("response_format"))
    backend_kwargs = dict(args)
    backend_kwargs.pop("response_format", None)
    audio_bytes, metadata = self.backend.synthesize(
      text=text,
      response_format=response_format,
      **backend_kwargs,
    )

    summary = TextChunk(data="Generated audio.")
    chunks.append(summary)
    yield summary
    audio_fmt = AudioFormat.WAV if response_format == "wav" else AudioFormat.MPEG
    audio = AudioChunk(
      data=audio_bytes,
      format=audio_fmt,
      metadata={
        "media_type": MEDIA_TYPES.get(response_format, f"audio/{response_format}"),
        "format": response_format.upper(),
        "model": self.model_name,
        "prompt": text,
        **metadata,
      },
    )
    chunks.append(audio)
    yield audio
    return ModelResponse(chunks=chunks, complete=True)

  def tokenize(self, text: str) -> List[int]:
    """Tokenization is not exposed for TTS backends."""
    raise NotImplementedError("TTSArchitecture does not expose tokenization.")

  def detokenize(self, tokens: List[int]) -> str:
    """Detokenization is not exposed for TTS backends."""
    raise NotImplementedError("TTSArchitecture does not expose detokenization.")

  def download(self, model_path: str) -> None:
    """Download support is delegated to backend packages."""
    raise NotImplementedError("TTSArchitecture does not implement standalone downloads.")

  def _create_backend(self, backend_name: str):
    if backend_name == "qwen3_tts":
      return Qwen3TTSBackend(
        model_name=self.model_name,
        model_path=self.model_path,
        device=self.device,
        dtype=self.dtype,
        api_token=self.api_token,
        **self.kwargs,
      )
    raise ValueError(f"Unsupported tts_backend '{backend_name}'.")

  def _resolve_text(self, inputs: ModelInputs, prompt_override: Optional[str]) -> str:
    """Resolve synthesis text from kwargs or text artifacts."""
    if prompt_override:
      return prompt_override

    artifacts = self._as_artifacts(inputs)
    for artifact in reversed(artifacts):
      if isinstance(artifact, TextArtifact) and artifact.content:
        return artifact.content
    raise ValueError("No text artifact found for speech generation.")

  @staticmethod
  def _as_artifacts(inputs: ModelInputs) -> List[BaseArtifact]:
    if isinstance(inputs, BaseArtifact):
      return [inputs]
    if isinstance(inputs, (list, tuple)):
      return list(inputs)
    raise TypeError("TTSArchitecture expects an artifact list input")

  def _normalize_response_format(self, response_format: Optional[str]) -> str:
    """Normalize response format for audio metadata and encoding."""
    normalized = (response_format or "wav").lower()
    if normalized not in MEDIA_TYPES:
      raise ValueError(f"Unsupported response_format '{response_format}'. Expected one of {sorted(MEDIA_TYPES)}.")
    return normalized


class Qwen3TTSBackend:
  """Adapter for the qwen-tts package."""

  def __init__(
    self,
    model_name: str,
    model_path: Optional[str],
    device: str,
    dtype: str,
    api_token: Optional[str] = None,
    **kwargs,
  ):
    self.model_name = model_name
    self.model_path = model_path
    self.device = device
    self.dtype = dtype
    self.api_token = api_token
    self.kwargs = kwargs
    self.model = None

  def load(self) -> None:
    try:
      torch = importlib.import_module("torch")
      qwen_tts = importlib.import_module("qwen_tts")
      Qwen3TTSModel = getattr(qwen_tts, "Qwen3TTSModel")
    except ImportError as e:
      raise ImportError(
        "qwen-tts is required for the qwen3_tts backend. "
        "Install it with `pip install qwen-tts` or `pip install claia[audio]`."
      ) from e

    load_kwargs: Dict[str, Any] = {
      "device_map": self._device_map(),
      "dtype": self._torch_dtype(torch),
    }
    if self.api_token:
      load_kwargs["token"] = self.api_token
    attn_implementation = self.kwargs.get("attn_implementation")
    if attn_implementation:
      load_kwargs["attn_implementation"] = attn_implementation

    self.model = Qwen3TTSModel.from_pretrained(
      self.model_path or self.model_name,
      **load_kwargs,
    )

  def unload(self) -> None:
    self.model = None

  def synthesize(
    self,
    text: str,
    response_format: str,
    **kwargs,
  ) -> Tuple[bytes, Dict[str, Any]]:
    if self.model is None:
      self.load()

    language = kwargs.get("language") or "English"
    reference_audio_path = kwargs.get("reference_audio_path")

    if hasattr(self.model, "generate_voice_clone"):
      if not reference_audio_path:
        raise ValueError(
          "Qwen3-TTS Base is a voice-cloning checkpoint and requires "
          "reference_audio_path. From the CLI, pass "
          "`--reference-audio-path /path/to/reference.wav`."
        )
      output = self.model.generate_voice_clone(
        text=text,
        language=language,
        ref_audio=reference_audio_path,
      )
    elif hasattr(self.model, "generate"):
      output = self.model.generate(text=text, language=language)
    else:
      raise AttributeError("Qwen3TTSModel exposes neither generate_voice_clone nor generate.")

    audio_bytes, sample_rate = self._normalize_output(output, response_format, kwargs.get("sample_rate"))
    return audio_bytes, {
      "language": language,
      "voice": kwargs.get("voice"),
      "sample_rate": sample_rate,
      "reference_audio_path": reference_audio_path,
    }

  def _normalize_output(self, output: Any, response_format: str, requested_sample_rate: Optional[int]) -> Tuple[bytes, Optional[int]]:
    if isinstance(output, bytes):
      return output, requested_sample_rate
    if isinstance(output, dict):
      audio = output.get("audio") or output.get("wav") or output.get("wavs")
      sample_rate = output.get("sample_rate") or output.get("sr") or requested_sample_rate
      return self._encode_audio(audio, sample_rate, response_format)
    if isinstance(output, tuple) and len(output) >= 2:
      return self._encode_audio(output[0], output[1], response_format)
    return self._encode_audio(output, requested_sample_rate, response_format)

  def _encode_audio(self, audio: Any, sample_rate: Optional[int], response_format: str) -> Tuple[bytes, Optional[int]]:
    if isinstance(audio, bytes):
      return audio, sample_rate
    if isinstance(audio, list) and audio:
      audio = audio[0]
    if sample_rate is None:
      raise ValueError("TTS backend returned waveform audio without a sample rate.")
    if response_format != "wav":
      raise ValueError("Only WAV output is currently supported for waveform TTS backends.")

    try:
      sf = importlib.import_module("soundfile")
    except ImportError as e:
      raise ImportError(
        "soundfile is required to encode waveform TTS output. "
        "Install it with `pip install soundfile` or `pip install claia[audio]`."
      ) from e

    buffer = io.BytesIO()
    sf.write(buffer, audio, int(sample_rate), format="WAV")
    return buffer.getvalue(), int(sample_rate)

  def _device_map(self) -> str:
    if self.device == "cuda":
      return "cuda:0"
    return self.device

  def _torch_dtype(self, torch_module):
    dtype = (self.dtype or "auto").lower()
    if dtype == "auto":
      return torch_module.float32 if self.device == "cpu" else torch_module.bfloat16
    if dtype == "float16":
      return torch_module.float16
    if dtype == "bfloat16":
      return torch_module.bfloat16
    if dtype == "float32":
      return torch_module.float32
    raise ValueError(f"Unsupported dtype '{self.dtype}'.")

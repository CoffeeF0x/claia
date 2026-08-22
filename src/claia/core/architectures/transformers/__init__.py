"""
Transformers-family architecture implementations.

In-process architectures served by the ``transformers`` deployment:
generic causal LMs, specialized families (Gemma3), Diffusers image
pipelines, and TTS.
"""

from .generic import GenericTransformerArchitecture
from .gemma3 import Gemma3Architecture
from .tts import TTSArchitecture

__all__ = ['GenericTransformerArchitecture', 'Gemma3Architecture', 'TTSArchitecture']

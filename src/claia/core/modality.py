"""
Modality declarations for model capability ads.

``Modality`` is the *declarative* side used on ``ModelDefinition`` to
advertise what kinds of input a model consumes and what kinds of output
it produces. Runtime IO payloads live under ``claia.core.data.artifacts``
and ``claia.core.data.chunks``; models return a ``ModelResponse``.
"""

from __future__ import annotations

from enum import Enum


class Modality(Enum):
  """Input or output medium for a model.

  Declared on ``ModelDefinition.input_modalities`` /
  ``output_modalities`` so the application can filter, route, and
  present models by what they handle. New modalities are purely
  additive; defaulting to ``[TEXT]`` preserves current behaviour.
  """
  TEXT = "text"
  IMAGE = "image"
  AUDIO = "audio"
  VIDEO = "video"
  EMBEDDING = "embedding"


__all__ = [
  "Modality",
]

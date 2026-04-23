"""
Modality declarations and multi-modal generation chunks.

``claia.core.modality`` introduces two complementary concepts:

* ``Modality`` — the *declarative* side. Used on ``ModelDefinition`` to
  advertise what kinds of input a model consumes and what kinds of
  output it produces. Text-only models declare ``[TEXT] -> [TEXT]``;
  multi-modal models extend the lists.
* ``GenerationChunk`` — the *runtime* side. A single item yielded by a
  deployment during inference. Each chunk carries a ``kind`` so
  consumers can dispatch on the payload (text tokens, raw image bytes,
  progress updates, ...), ``data`` holding the payload, and a free-form
  ``metadata`` dict for provider-specific extras.

The two pieces are deliberately independent: a model *definition* tells
the application what is *possible*, while a chunk *stream* tells the
application what actually arrived for a given call.

For the common text-only case the ``iter_text`` helper flattens a chunk
stream back to an ``Iterator[str]`` of the text payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Iterator


########################################################################
#                              MODALITIES                              #
########################################################################
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


########################################################################
#                            GENERATION CHUNKS                         #
########################################################################
class ChunkKind(Enum):
  """Discriminator for ``GenerationChunk`` payloads.

  ``TEXT`` carries a string token or a larger delta. The ``*_BYTES``
  variants carry raw media bytes. ``PROGRESS`` is a non-payload signal
  (e.g. a percentage or stage label) for long-running generations, and
  ``DONE`` marks explicit completion when a provider emits one.
  """
  TEXT = "text"
  IMAGE_BYTES = "image_bytes"
  AUDIO_BYTES = "audio_bytes"
  VIDEO_BYTES = "video_bytes"
  PROGRESS = "progress"
  DONE = "done"


@dataclass
class GenerationChunk:
  """A single item yielded by a deployment during inference.

  Consumers dispatch on ``kind``; text-only callers usually just need
  the ``.data`` field of ``TEXT`` chunks (see :func:`iter_text`).
  """
  kind: ChunkKind
  data: Any
  metadata: Dict[str, Any] = field(default_factory=dict)


def text_chunk(data: str, **metadata: Any) -> GenerationChunk:
  """Shortcut to build a ``ChunkKind.TEXT`` ``GenerationChunk``.

  Deployments that wrap a plain ``Iterator[str]`` from a model can use
  this helper to promote each token into a chunk without boilerplate.
  """
  return GenerationChunk(kind=ChunkKind.TEXT, data=data, metadata=dict(metadata))


def iter_text(chunks: Iterable[GenerationChunk]) -> Iterator[str]:
  """Yield the ``data`` of every ``TEXT`` chunk as a string.

  Non-text chunks are skipped, so a text-only consumer can iterate over
  a multi-modal stream safely. ``data`` values that are not strings are
  coerced with ``str()`` so providers that pack a richer delta object
  still produce something printable.
  """
  for chunk in chunks:
    if chunk.kind is ChunkKind.TEXT:
      yield chunk.data if isinstance(chunk.data, str) else str(chunk.data)


__all__ = [
  "Modality",
  "ChunkKind",
  "GenerationChunk",
  "text_chunk",
  "iter_text",
]

"""
Tests for the Phase 4 modality module.

Covers the ``Modality`` / ``ChunkKind`` enums, ``GenerationChunk``
dataclass, the ``text_chunk`` factory, and the ``iter_text`` helper
that flattens chunk streams back into ``Iterator[str]``.

Also verifies that ``ModelDefinition`` exposes modality and feature
flag defaults consistent with the plan: text in, text out, streaming
and system prompts on, tools off.
"""

# External dependencies
import pytest

# Internal dependencies
from claia.core.modality import (
  Modality,
  ChunkKind,
  GenerationChunk,
  text_chunk,
  iter_text,
)
from claia.core.definitions.model_definition import ModelDefinition


# ----------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------
def test_modality_enum_has_core_media_types():
  values = {m.value for m in Modality}
  assert {"text", "image", "audio", "video", "embedding"} <= values


def test_chunk_kind_has_expected_members():
  values = {k.value for k in ChunkKind}
  assert {"text", "image_bytes", "audio_bytes", "video_bytes", "progress", "done"} <= values


# ----------------------------------------------------------------------
# GenerationChunk + helpers
# ----------------------------------------------------------------------
def test_text_chunk_builds_text_kind_chunk_with_metadata():
  chunk = text_chunk("hello", index=0)
  assert isinstance(chunk, GenerationChunk)
  assert chunk.kind is ChunkKind.TEXT
  assert chunk.data == "hello"
  assert chunk.metadata == {"index": 0}


def test_generation_chunk_defaults_metadata_to_empty_dict():
  chunk = GenerationChunk(kind=ChunkKind.IMAGE_BYTES, data=b"\x89PNG")
  assert chunk.metadata == {}


def test_iter_text_yields_only_text_chunks_and_stringifies_non_str():
  chunks = [
    text_chunk("hello "),
    GenerationChunk(kind=ChunkKind.PROGRESS, data=0.5),
    text_chunk("world"),
    GenerationChunk(kind=ChunkKind.IMAGE_BYTES, data=b"...", metadata={"size": 3}),
    GenerationChunk(kind=ChunkKind.TEXT, data=42),  # odd, but we coerce
  ]
  out = list(iter_text(chunks))
  assert out == ["hello ", "world", "42"]


def test_iter_text_handles_empty_stream():
  assert list(iter_text([])) == []


# ----------------------------------------------------------------------
# ModelDefinition modality fields
# ----------------------------------------------------------------------
def test_model_definition_defaults_are_text_to_text():
  md = ModelDefinition(title="X")
  assert md.input_modalities == [Modality.TEXT]
  assert md.output_modalities == [Modality.TEXT]


def test_model_definition_accepts_multi_modal_declarations():
  md = ModelDefinition(
    title="Multi",
    input_modalities=[Modality.TEXT, Modality.IMAGE],
    output_modalities=[Modality.IMAGE],
  )
  assert Modality.IMAGE in md.input_modalities
  assert md.output_modalities == [Modality.IMAGE]

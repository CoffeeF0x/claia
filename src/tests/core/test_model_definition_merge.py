"""Unit tests for ``merge_model_definitions``.

Covers the generic field walk: ordered-union lists, overlay dicts,
and the not-None fallback for scalars.
"""

from claia.core.data.chunks import AudioChunk, ImageChunk, TextChunk
from claia.core.definitions.model_definition import (
  ModelDefinition,
  merge_model_definitions,
)
from claia.core.enums.data import ArtifactType
from claia.core.enums.parser import TagType
from claia.core.parser import TagSpec


def test_ordered_union_lists_dedupe_and_keep_first_seen_order():
  existing = ModelDefinition(
    aliases=["gpt", "chat"],
    architectures=["openai"],
    capabilities=["chat"],
    inputs=[ArtifactType.TEXT],
    outputs=[TextChunk],
  )
  incoming = ModelDefinition(
    aliases=["chat", "gpt-4"],
    architectures=["openai", "openrouter"],
    capabilities=["vision", "chat"],
    inputs=[ArtifactType.IMAGE, ArtifactType.TEXT],
    outputs=[ImageChunk, TextChunk],
  )

  merged = merge_model_definitions(existing, incoming)

  assert merged.aliases == ["gpt", "chat", "gpt-4"]
  assert merged.architectures == ["openai", "openrouter"]
  assert merged.capabilities == ["chat", "vision"]
  assert merged.inputs == [ArtifactType.TEXT, ArtifactType.IMAGE]
  assert merged.outputs == [TextChunk, ImageChunk]


def test_overlay_dicts_incoming_wins_per_key():
  existing = ModelDefinition(
    identifiers={"openai": "old-id", "anthropic": "keep-me"},
    tag_overrides={
      TagType.TOOL: TagSpec(TagType.TOOL, "<old>", "</old>"),
    },
  )
  incoming = ModelDefinition(
    identifiers={"openai": "new-id"},
    tag_overrides={
      TagType.TOOL: TagSpec(TagType.TOOL, "<new>", "</new>"),
      TagType.THINKING: TagSpec(TagType.THINKING, "<t>", "</t>"),
    },
  )

  merged = merge_model_definitions(existing, incoming)

  assert merged.identifiers == {"openai": "new-id", "anthropic": "keep-me"}
  assert merged.tag_overrides is not None
  assert merged.tag_overrides[TagType.TOOL] == incoming.tag_overrides[TagType.TOOL]
  assert merged.tag_overrides[TagType.THINKING] == incoming.tag_overrides[TagType.THINKING]


def test_tag_overrides_none_stays_none():
  merged = merge_model_definitions(ModelDefinition(), ModelDefinition())
  assert merged.tag_overrides is None


def test_tag_overrides_only_existing_preserved():
  existing = ModelDefinition(
    tag_overrides={TagType.TOOL: TagSpec(TagType.TOOL, "<a>", "</a>")},
  )
  merged = merge_model_definitions(existing, ModelDefinition())
  assert merged.tag_overrides == existing.tag_overrides


def test_tag_overrides_only_incoming_preserved():
  incoming = ModelDefinition(
    tag_overrides={TagType.TOOL: TagSpec(TagType.TOOL, "<a>", "</a>")},
  )
  merged = merge_model_definitions(ModelDefinition(), incoming)
  assert merged.tag_overrides == incoming.tag_overrides


def test_merge_does_not_mutate_inputs():
  existing = ModelDefinition(
    aliases=["a"],
    identifiers={"k": "v"},
    tag_overrides={TagType.TOOL: TagSpec(TagType.TOOL, "<a>", "</a>")},
  )
  incoming = ModelDefinition(
    aliases=["b"],
    identifiers={"k": "w"},
    tag_overrides={TagType.THINKING: TagSpec(TagType.THINKING, "<b>", "</b>")},
  )
  existing_aliases = list(existing.aliases)
  existing_ids = dict(existing.identifiers)
  existing_tags = dict(existing.tag_overrides)
  incoming_aliases = list(incoming.aliases)
  incoming_ids = dict(incoming.identifiers)
  incoming_tags = dict(incoming.tag_overrides)

  merge_model_definitions(existing, incoming)

  assert existing.aliases == existing_aliases
  assert existing.identifiers == existing_ids
  assert existing.tag_overrides == existing_tags
  assert incoming.aliases == incoming_aliases
  assert incoming.identifiers == incoming_ids
  assert incoming.tag_overrides == incoming_tags


def test_scalar_fallback_incoming_if_not_none():
  existing = ModelDefinition(
    title="Old",
    company="Acme",
    description="keep-if-incoming-empty",
    context_length=128,
  )
  incoming = ModelDefinition(
    title="New",
    company=None,
    description=None,
    context_length=256,
  )

  merged = merge_model_definitions(existing, incoming)

  assert merged.title == "New"
  assert merged.company == "Acme"
  assert merged.description == "keep-if-incoming-empty"
  assert merged.context_length == 256


def test_later_provider_default_io_unions_with_existing():
  existing = ModelDefinition(
    inputs=[ArtifactType.TEXT, ArtifactType.IMAGE],
    outputs=[TextChunk, AudioChunk],
  )
  incoming = ModelDefinition()

  merged = merge_model_definitions(existing, incoming)

  assert ArtifactType.TEXT in merged.inputs
  assert ArtifactType.IMAGE in merged.inputs
  assert TextChunk in merged.outputs
  assert AudioChunk in merged.outputs

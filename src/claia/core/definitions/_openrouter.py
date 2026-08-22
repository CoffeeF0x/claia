"""Shared builder for OpenRouter-only company definition modules."""

from typing import List, Optional

from .model_definition import ModelDefinition
from ..data.chunks import TextChunk
from ..data.models.conversation.message_sequence import MessageSequence
from ..enums.data import ArtifactType


TEXT = [ArtifactType.TEXT, MessageSequence]
VISION = [ArtifactType.TEXT, ArtifactType.IMAGE, MessageSequence]
TEXT_OUT = [TextChunk]


def definition(
  title: str,
  provider_id: str,
  company: str,
  description: str,
  context_length: int,
  capabilities: List[str],
  aliases: Optional[List[str]] = None,
  inputs: Optional[List] = None,
  license: str = "Commercial",
  url: Optional[str] = None,
) -> ModelDefinition:
  """Build a definition that is only reachable through OpenRouter."""
  return ModelDefinition(
    title=title,
    aliases=aliases,
    company=company,
    deployments=["api"],
    architectures=["openrouter"],
    description=description,
    context_length=context_length,
    capabilities=capabilities,
    license=license,
    url=url or f"https://openrouter.ai/models/{provider_id}",
    identifiers={"openrouter": provider_id},
    inputs=inputs or TEXT,
    outputs=TEXT_OUT,
  )

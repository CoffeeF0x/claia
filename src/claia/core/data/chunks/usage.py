"""Usage chunk — normalized token accounting from a provider."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ...enums.data import ApplicationFormat, MediaType

from .base import BaseChunk


class UsageChunk(BaseChunk):
  """Token accounting for one generate call.

  Named fields are the contract. The raw provider payload may ride
  in ``metadata`` for debugging. Agents never append this to the
  streaming message.
  """

  def __init__(
    self,
    token_input: Optional[int] = None,
    token_output: Optional[int] = None,
    total_tokens: Optional[int] = None,
    cached_tokens: Optional[int] = None,
    reasoning_tokens: Optional[int] = None,
    finish_reason: Optional[str] = None,
    provider: Optional[str] = None,
    provider_model: Optional[str] = None,
    name: str = "usage",
    metadata: Optional[Dict[str, Any]] = None,
  ):
    super().__init__(
      type=MediaType.APPLICATION,
      format=ApplicationFormat.JSON,
      name=name,
      metadata=metadata,
      data={
        "token_input": token_input,
        "token_output": token_output,
        "total_tokens": total_tokens,
        "cached_tokens": cached_tokens,
        "reasoning_tokens": reasoning_tokens,
        "finish_reason": finish_reason,
        "provider": provider,
        "provider_model": provider_model,
      },
    )
    self.token_input = token_input
    self.token_output = token_output
    self.total_tokens = total_tokens
    self.cached_tokens = cached_tokens
    self.reasoning_tokens = reasoning_tokens
    self.finish_reason = finish_reason
    self.provider = provider
    self.provider_model = provider_model

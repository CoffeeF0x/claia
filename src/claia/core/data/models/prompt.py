"""
Prompt data model.

Conversation-domain prompt object — not an artifact. Host runtimes
persist prompts independently of the IO artifact hierarchy.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class Prompt:
  """Prompt model with validated slug name and optional text body."""

  def __init__(
    self,
    name: str = "untitled-prompt.json",
    prompt_name: Optional[str] = None,
    prompt_type: str = "text",
    id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[float] = None,
    updated_at: Optional[float] = None,
    **kwargs,
  ):
    del kwargs  # accept and ignore legacy artifact kwargs
    if not name.endswith(".json"):
      name = f"{name}.json"

    self.id = id or str(uuid.uuid4())
    self.name = name
    self.prompt_name = (
      self.validate_prompt_name(prompt_name)
      if prompt_name
      else self._extract_name(name)
    )
    self.prompt_type = prompt_type
    self.metadata: Dict[str, Any] = metadata or {}
    self.metadata["prompt_name"] = self.prompt_name
    self.metadata["prompt_type"] = self.prompt_type
    self.created_at = created_at or time.time()
    self.updated_at = updated_at or self.created_at
    self._content: Optional[str] = None

  def _extract_name(self, name: str) -> str:
    return self.validate_prompt_name(name.replace(".json", ""))

  @staticmethod
  def validate_prompt_name(name: str) -> str:
    if not name:
      return "untitled-prompt"
    name = name.lower()
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^a-z0-9-]", "", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    return name or "untitled-prompt"

  def load_content(self) -> str:
    return self._content or ""

  def set_content(self, content: str) -> None:
    self._content = content
    self.updated_at = time.time()

  @property
  def content(self) -> str:
    return self.load_content()

  def to_dict(self) -> Dict[str, Any]:
    data = {
      "id": self.id,
      "name": self.name,
      "prompt_name": self.prompt_name,
      "prompt_type": self.prompt_type,
      "metadata": self.metadata,
      "created_at": self.created_at,
      "updated_at": self.updated_at,
    }
    if self._content is not None:
      data["content"] = self._content
    return data

  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> Prompt:
    prompt = cls(
      name=data.get("name", "untitled-prompt.json"),
      id=data.get("id"),
      prompt_name=data.get("prompt_name") or data.get("metadata", {}).get("prompt_name"),
      prompt_type=data.get("prompt_type", "text")
      or data.get("metadata", {}).get("prompt_type"),
      metadata=data.get("metadata", {}),
      created_at=data.get("created_at"),
      updated_at=data.get("updated_at"),
    )
    if data.get("content") is not None:
      prompt._content = data["content"]
    return prompt

  @classmethod
  def from_content(
    cls,
    content: str,
    prompt_name: str,
    prompt_type: str = "text",
    **kwargs,
  ) -> Prompt:
    validated_name = cls.validate_prompt_name(prompt_name)
    name = kwargs.pop("name", f"{validated_name}.json")
    prompt = cls(
      name=name,
      prompt_name=validated_name,
      prompt_type=prompt_type,
      **kwargs,
    )
    prompt.set_content(content)
    return prompt

  @classmethod
  def from_path(cls, source: str, **kwargs) -> Prompt:
    import os
    name = kwargs.pop("name", os.path.basename(source))
    if not name.endswith(".json"):
      name = f"{name}.json"
    prompt_name = kwargs.pop("prompt_name", name.replace(".json", ""))
    prompt = cls(name=name, prompt_name=prompt_name, **kwargs)
    prompt.metadata["source_uri"] = source
    return prompt

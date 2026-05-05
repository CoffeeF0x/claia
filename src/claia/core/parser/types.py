"""
Core types for the streaming tag parser.

The parser produces a stream of ``ParseEvent`` items as it consumes
chunks of model output:

- ``TextEvent`` — a span of plain text outside any tag.
- ``TagEvent`` — a fully closed tag with its content and attributes.
- ``ParseError`` — a structural problem (mismatched close, unclosed
  tags at flush). Surfaced in-band so consumers can choose to ignore.

Tag identity is the categorical ``TagType`` — the actual delimiter
strings live on the ``TagSpec`` and are model-specific. ``TagType``
stays stable across models so downstream dispatch (the agent decides
to forward TOOL events to the registry, log THINKING events, etc.)
does not need to inspect the delimiter strings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Union


########################################################################
#                              TAG TYPE                                #
########################################################################
class TagType(Enum):
  """Categorical kind of a parsed tag span.

  The set is intentionally small at the start; new categories are
  added as new tag-shaped artifacts are introduced (e.g., a future
  ``CODE`` for opaque code blocks). The string value is stable and
  used for serialization / persistence of utility messages.
  """
  TOOL = "tool"
  THINKING = "thinking"
  REFERENCE = "reference"


########################################################################
#                              TAG SPEC                                #
########################################################################
@dataclass(frozen=True)
class TagSpec:
  """Concrete description of a single tag's delimiters.

  ``open_token`` is interpreted in one of two ways:

  - ``attribute_terminator is None``: ``open_token`` is matched
    verbatim first (e.g., ``[TOOL_CALL]`` matches ``[TOOL_CALL]``
    exactly with empty attributes). If the literal does not match
    and ``len(open_token) > 1``, the parser falls back to an
    *inferred-terminator* match using ``open_token[-1]`` as the
    terminator and ``open_token[:-1]`` as the prefix; the character
    immediately after the prefix must be the terminator or
    whitespace, which lets ``<think foo="x">`` match without making
    ``<thinking>`` match against ``<think>``.
  - ``attribute_terminator`` is a string (e.g., ``]`` or ``>``):
    ``open_token`` is the opening **prefix**. After the prefix, the
    parser tolerates whitespace and ``key=value`` attribute pairs up
    to the terminator (e.g., ``[TOOL_CALL`` … ``]`` or
    ``<reference`` … ``>``).

  A single parser instance must not be configured with two specs
  whose open tokens prefix-match each other; the constructor of
  ``TagParser`` enforces one spec per ``TagType`` which
  prevents the most common collision.
  """
  tag_type: TagType
  open_token: str
  close_token: str
  attribute_terminator: Optional[str] = None


########################################################################
#                            PARSE EVENTS                              #
########################################################################
@dataclass(frozen=True)
class TextEvent:
  """A span of plain text consumed outside any open tag."""
  text: str
  start_index: int
  end_index: int  # exclusive


@dataclass(frozen=True)
class TagEvent:
  """A fully matched ``<open>…</close>`` span.

  ``content`` is the raw text between the open and close tokens,
  delivered verbatim. The parser never interprets it (no JSON / no
  XML decode); per-tag-type decoding belongs to the consumer (the
  simple protocol JSON-decodes TOOL content, etc.).
  """
  tag_type: TagType
  content: str
  attributes: Dict[str, str] = field(default_factory=dict)
  start_index: int = 0
  end_index: int = 0  # exclusive; just past the close token
  raw_open: str = ""
  raw_close: str = ""


@dataclass(frozen=True)
class ParseError:
  """A structural error surfaced as a parse event.

  ``reason`` is a short, machine-readable code:

  - ``"mismatched_close"`` — a recognized close token was encountered
    that does not match the top of the open-tag stack. The token is
    consumed as plain content and the stack is left unchanged.
  - ``"unclosed_tags"`` — emitted by ``flush()`` when end-of-stream
    is reached with the stack non-empty. ``expected`` is the close
    token of the top unclosed tag.

  Consumers may ignore these events; they do not interrupt the
  iterator.
  """
  reason: str
  position: int
  expected: Optional[str] = None
  got: Optional[str] = None


ParseEvent = Union[TextEvent, TagEvent, ParseError]

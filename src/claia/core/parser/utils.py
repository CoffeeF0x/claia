"""Internal helpers for the parser package: prefix tests, attribute regions, open-tag frames."""

from typing import Dict, Tuple, Union

from .types import TagSpec

KEY_CHARS = set(
  "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_."
)
WHITESPACE = (' ', '\t', '\r', '\n')


def is_proper_prefix(s: str, target: str) -> bool:
  """True iff ``s`` is a non-empty proper prefix of ``target``."""
  return 0 < len(s) < len(target) and target.startswith(s)


ParseResult = Union[
  Tuple[str, Dict[str, str], int],  # ("complete", attrs, end_index)
  Tuple[str],                       # ("partial",) or ("malformed",)
]


def parse_attribute_region(buffer: str, start: int, terminator: str) -> ParseResult:
  """Parse the attribute region of a prefix-style open token.

  When a ``TagSpec`` declares an ``attribute_terminator``, the open token is
  a prefix; the region after it may contain XML-style ``key=value`` pairs until
  the terminator.

  Returns one of:

  - ``("complete", attributes_dict, end_index)`` — terminator found;
    ``end_index`` is just past it.
  - ``("partial",)`` — need more input before the terminator.
  - ``("malformed",)`` — not a valid attribute region; the caller should
    treat this as not an opening tag.

  Args:
    buffer: The full streaming buffer.
    start: Index of the first character after the open prefix.
    terminator: The close-of-open string (e.g., ``"]"`` or ``">"``).

  Raises:
    ValueError: if ``terminator`` is empty.
  """
  if not terminator:
    raise ValueError("attribute_terminator must be a non-empty string")

  attrs: Dict[str, str] = {}
  cursor = start
  n = len(buffer)

  while True:
    while cursor < n and buffer[cursor] in WHITESPACE:
      cursor += 1
    if cursor >= n:
      return ("partial",)

    if buffer.startswith(terminator, cursor):
      return ("complete", attrs, cursor + len(terminator))
    if is_proper_prefix(buffer[cursor:], terminator):
      return ("partial",)

    if buffer[cursor] not in KEY_CHARS:
      return ("malformed",)

    key_start = cursor
    while cursor < n and buffer[cursor] in KEY_CHARS:
      cursor += 1
    if cursor >= n:
      return ("partial",)
    key = buffer[key_start:cursor]

    if buffer[cursor] != '=':
      attrs[key] = ""
      continue

    cursor += 1
    if cursor >= n:
      return ("partial",)

    if buffer[cursor] in ("'", '"'):
      quote = buffer[cursor]
      cursor += 1
      val_start = cursor
      while cursor < n and buffer[cursor] != quote:
        cursor += 1
      if cursor >= n:
        return ("partial",)
      attrs[key] = buffer[val_start:cursor]
      cursor += 1
      continue

    val_start = cursor
    while cursor < n:
      ch = buffer[cursor]
      if ch in WHITESPACE:
        break
      if buffer.startswith(terminator, cursor):
        break
      cursor += 1
    if cursor >= n:
      return ("partial",)
    attrs[key] = buffer[val_start:cursor]


class OpenTag:
  """A tag whose open token was consumed but whose close has not yet been seen."""

  __slots__ = ("spec", "attributes", "open_start", "content_start", "raw_open")

  def __init__(
    self,
    spec: TagSpec,
    attributes: Dict[str, str],
    open_start: int,
    content_start: int,
    raw_open: str,
  ) -> None:
    self.spec = spec
    self.attributes = attributes
    self.open_start = open_start
    self.content_start = content_start
    self.raw_open = raw_open

"""
Attribute-region parser.

When a ``TagSpec`` declares an ``attribute_terminator`` the open token
is treated as a prefix; the region between the prefix and the
terminator may carry a sequence of XML-style ``key=value`` attributes.

This module provides ``parse_attribute_region`` which scans that
region and returns one of three statuses:

- ``("complete", attributes_dict, end_index)`` — the terminator was
  found; ``end_index`` is the position just past it.
- ``("partial",)`` — the buffer ran out before the terminator was
  found. The streaming parser holds back and waits for more input.
- ``("malformed",)`` — the region is structurally invalid (e.g., the
  prefix matched but the next character cannot start an attribute
  key, the terminator, or whitespace). The streaming parser treats
  this as "not actually an opening tag" and continues with the
  prefix consumed as plain text/content.

The separation keeps streaming book-keeping (when do we have enough
input?) inside this module, so the higher-level state machine in
``streaming.py`` only deals with whole-tag decisions.
"""

from typing import Dict, Tuple, Union


########################################################################
#                          ATTRIBUTE PARSER                            #
########################################################################
_KEY_CHARS = set(
  "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_."
)
_WHITESPACE = (' ', '\t', '\r', '\n')


ParseResult = Union[
  Tuple[str, Dict[str, str], int],  # ("complete", attrs, end_index)
  Tuple[str],                       # ("partial",) or ("malformed",)
]


def parse_attribute_region(buffer: str, start: int, terminator: str) -> ParseResult:
  """Parse the attribute region of a prefix-style open token.

  Args:
    buffer: The full streaming buffer.
    start: Index of the first character after the open prefix
      (i.e., where attributes / whitespace / the terminator begin).
    terminator: The close-of-open string (e.g., ``"]"`` or ``">"``).

  Returns:
    A tagged tuple as described in the module docstring.
  """
  if not terminator:
    raise ValueError("attribute_terminator must be a non-empty string")

  attrs: Dict[str, str] = {}
  cursor = start
  n = len(buffer)

  while True:
    while cursor < n and buffer[cursor] in _WHITESPACE:
      cursor += 1
    if cursor >= n:
      return ("partial",)

    if buffer.startswith(terminator, cursor):
      return ("complete", attrs, cursor + len(terminator))
    if _is_proper_prefix(buffer[cursor:], terminator):
      return ("partial",)

    if buffer[cursor] not in _KEY_CHARS:
      return ("malformed",)

    key_start = cursor
    while cursor < n and buffer[cursor] in _KEY_CHARS:
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
      if ch in _WHITESPACE:
        break
      if buffer.startswith(terminator, cursor):
        break
      cursor += 1
    if cursor >= n:
      return ("partial",)
    attrs[key] = buffer[val_start:cursor]


def _is_proper_prefix(s: str, target: str) -> bool:
  """True iff ``s`` is a non-empty proper prefix of ``target``."""
  return 0 < len(s) < len(target) and target.startswith(s)

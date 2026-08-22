"""
Stateful streaming tag parser.

``TagParser`` consumes assistant output one chunk at a time and yields
``ParseEvent`` items as they become unambiguous. It is used by the agent loop
today and is reused for any tag-shaped artifact in model text (tool calls,
thinking, references, …).

State machine, informally:

1. The parser maintains a buffer of all input received so far, a scan
   cursor, the start position of pending plain text, and a LIFO
   stack of open tags.
2. At every position it tries to match (a) a close token of the top
   of the stack, (b) a close token of any other active spec, or
   (c) an open token of any active spec. Matches resolve as
   *complete*, *partial* (need more input — stop scanning), or
   *no match* (advance one character).
3. Completing an open emits any pending ``TextEvent``, pushes the
   open onto the stack, and notes the open's content-start position.
4. Completing the close of the stack top pops the stack and emits a
   ``TagEvent`` whose ``content`` spans from the popped open's
   content-start up to (but excluding) the close token.
5. Completing the close of a non-top spec emits a
   ``ParseError(reason="mismatched_close")`` and continues — the
   close text is consumed as content of the current top tag.
6. ``flush()`` emits any pending ``TextEvent`` and, if the stack is
   not empty, emits ``ParseError(reason="unclosed_tags")``.

The parser does NOT drop bytes from its buffer; absolute event
positions are simply buffer indices. See the implementation notes for
why this is acceptable for v1.
"""

from typing import Dict, Iterable, Iterator, List, Tuple

from ..enums.parser import TagType
from .types import ParseError, ParseEvent, TagEvent, TagSpec, TextEvent
from .utils import OpenTag, is_proper_prefix, parse_attribute_region


########################################################################
#                             TAG PARSER                               #
########################################################################
class TagParser:
  """Tag-extraction state machine over streamed text chunks.

  Construct with the active set of tag specs (typically produced by
  ``resolve_tag_specs(model_def)``). At most one spec per
  ``TagType`` is permitted; a duplicate raises ``ValueError`` at
  construction time.
  """

  def __init__(self, tag_specs: Iterable[TagSpec]) -> None:
    specs = list(tag_specs)
    seen: Dict[TagType, TagSpec] = {}
    for spec in specs:
      if spec.tag_type in seen:
        raise ValueError(
          f"Duplicate TagSpec for {spec.tag_type!r}: "
          f"{seen[spec.tag_type]!r} vs {spec!r}"
        )
      seen[spec.tag_type] = spec
    self._specs: List[TagSpec] = specs

    self._buffer: str = ""
    self._scan_pos: int = 0
    self._text_start: int = 0
    self._stack: List[OpenTag] = []

  # ------------------------------------------------------------------
  # Public API
  # ------------------------------------------------------------------
  def feed(self, chunk: str) -> Iterator[ParseEvent]:
    """Consume a chunk of input; yield any events that become unambiguous."""
    if chunk:
      self._buffer += chunk
    yield from self._scan()

  def flush(self) -> Iterator[ParseEvent]:
    """Signal end-of-stream. Yield any final events.

    Emits a final ``TextEvent`` if there is pending text outside any
    tag, and a ``ParseError(reason="unclosed_tags")`` for each open
    tag still on the stack (outermost first).
    """
    yield from self._scan()
    if not self._stack and self._text_start < len(self._buffer):
      yield TextEvent(
        text=self._buffer[self._text_start:],
        start_index=self._text_start,
        end_index=len(self._buffer),
      )
      self._text_start = len(self._buffer)
    while self._stack:
      top = self._stack.pop(0)  # outermost first
      yield ParseError(
        reason="unclosed_tags",
        position=len(self._buffer),
        expected=top.spec.close_token,
        got=None,
      )
    self._scan_pos = len(self._buffer)

  # ------------------------------------------------------------------
  # Core scan loop
  # ------------------------------------------------------------------
  def _scan(self) -> Iterator[ParseEvent]:
    while self._scan_pos < len(self._buffer):
      p = self._scan_pos

      if self._stack:
        close_outcome = self._try_match_close(p)
        kind = close_outcome[0]
        if kind == "complete_top":
          end_pos = close_outcome[1]
          yield self._pop_and_build_tag_event(p, end_pos)
          continue
        if kind == "complete_mismatch":
          end_pos = close_outcome[2]
          yield ParseError(
            reason="mismatched_close",
            position=p,
            expected=self._stack[-1].spec.close_token,
            got=self._buffer[p:end_pos],
          )
          self._scan_pos = end_pos
          continue
        if kind == "partial":
          return

      open_outcome = self._try_match_open(p)
      kind = open_outcome[0]
      if kind == "complete":
        spec, attrs, raw_open, end_pos = open_outcome[1:]
        if not self._stack and p > self._text_start:
          yield TextEvent(
            text=self._buffer[self._text_start:p],
            start_index=self._text_start,
            end_index=p,
          )
        self._stack.append(OpenTag(
          spec=spec,
          attributes=attrs,
          open_start=p,
          content_start=end_pos,
          raw_open=raw_open,
        ))
        self._scan_pos = end_pos
        self._text_start = end_pos
        continue
      if kind == "partial":
        return

      self._scan_pos += 1

  # ------------------------------------------------------------------
  # Close-token matching
  # ------------------------------------------------------------------
  def _try_match_close(self, p: int) -> Tuple:
    """Try to match a close token at ``p``.

    Returns one of:
      ``("complete_top", end_pos)``
      ``("complete_mismatch", spec, end_pos)``
      ``("partial",)``
      ``("no_match",)``
    """
    any_partial = False
    top_spec = self._stack[-1].spec

    ct = top_spec.close_token
    if self._buffer.startswith(ct, p):
      return ("complete_top", p + len(ct))
    if is_proper_prefix(self._buffer[p:], ct):
      any_partial = True

    for spec in self._specs:
      if spec is top_spec:
        continue
      ct = spec.close_token
      if self._buffer.startswith(ct, p):
        return ("complete_mismatch", spec, p + len(ct))
      if is_proper_prefix(self._buffer[p:], ct):
        any_partial = True

    return ("partial",) if any_partial else ("no_match",)

  # ------------------------------------------------------------------
  # Open-token matching
  # ------------------------------------------------------------------
  def _try_match_open(self, p: int) -> Tuple:
    """Try to match an open token at ``p``.

    Returns one of:
      ``("complete", spec, attributes, raw_open, end_pos)``
      ``("partial",)``
      ``("no_match",)``

    For specs with an explicit ``attribute_terminator`` the
    ``open_token`` is the prefix and attributes are parsed up to the
    terminator. For specs with ``attribute_terminator=None`` the
    parser first tries a verbatim match of ``open_token``; if that
    fails AND the token is at least two characters long, it falls
    back to an "inferred terminator" match using ``open_token[-1]``
    as the terminator and ``open_token[:-1]`` as the prefix. The
    fallback path requires the character immediately after the
    prefix to be either the inferred terminator or whitespace, so
    that e.g. ``<think>`` does not match against ``<thinking>``.
    """
    any_partial = False

    for spec in self._specs:
      ot = spec.open_token

      if spec.attribute_terminator is None:
        if self._buffer.startswith(ot, p):
          return ("complete", spec, {}, ot, p + len(ot))
        if is_proper_prefix(self._buffer[p:], ot):
          any_partial = True
          continue
        if len(ot) > 1:
          inferred = self._try_match_inferred_open(spec, p)
          if inferred[0] == "complete":
            return inferred
          if inferred[0] == "partial":
            any_partial = True
        continue

      if self._buffer.startswith(ot, p):
        outcome = parse_attribute_region(
          self._buffer,
          p + len(ot),
          spec.attribute_terminator,
        )
        if outcome[0] == "complete":
          attrs, end_pos = outcome[1], outcome[2]
          raw_open = self._buffer[p:end_pos]
          return ("complete", spec, attrs, raw_open, end_pos)
        if outcome[0] == "partial":
          any_partial = True
          continue
        # malformed — fall through; treat as not actually an open here.
        continue

      if is_proper_prefix(self._buffer[p:], ot):
        any_partial = True

    return ("partial",) if any_partial else ("no_match",)

  def _try_match_inferred_open(self, spec: TagSpec, p: int) -> Tuple:
    """Try the inferred-terminator fallback for a no-explicit-terminator spec.

    Treats ``spec.open_token[:-1]`` as the prefix and
    ``spec.open_token[-1]`` as the terminator. Returns a tuple shaped
    like the outer ``_try_match_open`` result, or ``("no_match",)``
    when this spec does not in fact open here.
    """
    ot = spec.open_token
    prefix = ot[:-1]
    terminator = ot[-1]

    if not self._buffer.startswith(prefix, p):
      return ("no_match",)

    after = p + len(prefix)
    if after >= len(self._buffer):
      return ("partial",)

    next_ch = self._buffer[after]
    if next_ch != terminator and not next_ch.isspace():
      return ("no_match",)

    outcome = parse_attribute_region(self._buffer, after, terminator)
    if outcome[0] == "complete":
      attrs, end_pos = outcome[1], outcome[2]
      raw_open = self._buffer[p:end_pos]
      return ("complete", spec, attrs, raw_open, end_pos)
    if outcome[0] == "partial":
      return ("partial",)
    return ("no_match",)

  # ------------------------------------------------------------------
  # Tag-event construction
  # ------------------------------------------------------------------
  def _pop_and_build_tag_event(self, close_start: int, close_end: int) -> TagEvent:
    top = self._stack.pop()
    raw_close = self._buffer[close_start:close_end]
    event = TagEvent(
      tag_type=top.spec.tag_type,
      content=self._buffer[top.content_start:close_start],
      attributes=dict(top.attributes),
      start_index=top.open_start,
      end_index=close_end,
      raw_open=top.raw_open,
      raw_close=raw_close,
    )
    self._scan_pos = close_end
    if not self._stack:
      self._text_start = close_end
    return event

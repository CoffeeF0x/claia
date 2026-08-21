"""
Tests for the streaming tag parser (Phase 1 of the tools overhaul).

Covers:
- Text-only streams
- Simple non-attributed tag spans
- Text events between tags
- Attributed tags in XML and bracket styles, with all attribute
  forms (double quoted, single quoted, unquoted, bare key)
- Nested tags in strict LIFO order
- Mismatched close tokens
- Non-empty stack at flush
- Tags split across chunk boundaries (every legal break point of a
  representative fixture)
- Default tag spec resolution and per-model override merging
"""

# External dependencies
import pytest
from types import SimpleNamespace
from typing import List

# Internal dependencies
from claia.core.parser import (
  DEFAULT_TAGS,
  ParseError,
  ParseEvent,
  TagEvent,
  TagParser,
  TagSpec,
  TagType,
  TextEvent,
  resolve_tag_specs,
)


########################################################################
#                              FIXTURES                                #
########################################################################
@pytest.fixture
def default_specs() -> List[TagSpec]:
  return list(DEFAULT_TAGS.values())


@pytest.fixture
def parser(default_specs: List[TagSpec]) -> TagParser:
  return TagParser(default_specs)


def _events(parser: TagParser, *chunks: str) -> List[ParseEvent]:
  """Feed all ``chunks`` then flush; return the full event list."""
  out: List[ParseEvent] = []
  for c in chunks:
    out.extend(parser.feed(c))
  out.extend(parser.flush())
  return out


########################################################################
#                            BASIC STREAMS                             #
########################################################################
class TestBasicStreams:
  def test_text_only_flushes_correctly(self, parser):
    events = _events(parser, "Hello world, no tags here.")
    assert len(events) == 1
    assert isinstance(events[0], TextEvent)
    assert events[0].text == "Hello world, no tags here."
    assert events[0].start_index == 0
    assert events[0].end_index == len("Hello world, no tags here.")

  def test_empty_stream(self, parser):
    events = _events(parser)
    assert events == []

  def test_empty_chunks(self, parser):
    events = _events(parser, "", "Hi", "", "")
    assert len(events) == 1
    assert isinstance(events[0], TextEvent)
    assert events[0].text == "Hi"


########################################################################
#                           UNATTRIBUTED TAGS                          #
########################################################################
class TestSimpleTags:
  def test_single_tool_call(self, parser):
    events = _events(parser, '[TOOL_CALL]{"name":"x"}[/TOOL_CALL]')
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.tag_type == TagType.TOOL
    assert ev.content == '{"name":"x"}'
    assert ev.attributes == {}
    assert ev.start_index == 0
    assert ev.end_index == len('[TOOL_CALL]{"name":"x"}[/TOOL_CALL]')
    assert ev.raw_open == "[TOOL_CALL]"
    assert ev.raw_close == "[/TOOL_CALL]"

  def test_text_around_tag(self, parser):
    text = "before [TOOL_CALL]inner[/TOOL_CALL] after"
    events = _events(parser, text)
    assert len(events) == 3
    pre, tag, post = events
    assert isinstance(pre, TextEvent)
    assert pre.text == "before "
    assert pre.start_index == 0
    assert pre.end_index == 7
    assert isinstance(tag, TagEvent)
    assert tag.tag_type == TagType.TOOL
    assert tag.content == "inner"
    assert tag.start_index == 7
    assert tag.end_index == 7 + len("[TOOL_CALL]inner[/TOOL_CALL]")
    assert isinstance(post, TextEvent)
    assert post.text == " after"
    assert post.start_index == tag.end_index
    assert post.end_index == len(text)

  def test_thinking_tag(self, parser):
    events = _events(parser, "<think>I should consider this</think>done")
    assert len(events) == 2
    tag, post = events
    assert isinstance(tag, TagEvent)
    assert tag.tag_type == TagType.THINKING
    assert tag.content == "I should consider this"
    assert isinstance(post, TextEvent)
    assert post.text == "done"

  def test_two_consecutive_tags(self, parser):
    events = _events(parser, "<think>a</think><think>b</think>")
    assert len(events) == 2
    assert all(isinstance(ev, TagEvent) for ev in events)
    assert [ev.content for ev in events] == ["a", "b"]


########################################################################
#                          ATTRIBUTED TAGS                             #
########################################################################
class TestAttributedTags:
  @pytest.fixture
  def attr_specs(self) -> List[TagSpec]:
    return [
      TagSpec(
        tag_type=TagType.REFERENCE,
        open_token="<reference",
        close_token="</reference>",
        attribute_terminator=">",
      ),
      TagSpec(
        tag_type=TagType.TOOL,
        open_token="[TOOL_CALL",
        close_token="[/TOOL_CALL]",
        attribute_terminator="]",
      ),
    ]

  def test_xml_double_quoted(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(parser, '<reference guid="abc-123">body</reference>')
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.tag_type == TagType.REFERENCE
    assert ev.content == "body"
    assert ev.attributes == {"guid": "abc-123"}
    assert ev.raw_open == '<reference guid="abc-123">'
    assert ev.raw_close == "</reference>"

  def test_bracket_single_quoted(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(parser, "[TOOL_CALL NAME='do_thing']content[/TOOL_CALL]")
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.tag_type == TagType.TOOL
    assert ev.content == "content"
    assert ev.attributes == {"NAME": "do_thing"}

  def test_unquoted_value(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(parser, "<reference guid=plain>body</reference>")
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.attributes == {"guid": "plain"}

  def test_bare_key_no_value(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(parser, "<reference flag>body</reference>")
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.attributes == {"flag": ""}

  def test_multiple_attributes(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(
      parser,
      "<reference guid=\"x\" type='thing' weight=42 sticky>body</reference>",
    )
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.attributes == {
      "guid": "x",
      "type": "thing",
      "weight": "42",
      "sticky": "",
    }

  def test_no_attributes(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(parser, "[TOOL_CALL]bare[/TOOL_CALL]")
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.content == "bare"
    assert ev.attributes == {}

  def test_attribute_with_dotted_key(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(parser, '<reference my.key="v">body</reference>')
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.attributes == {"my.key": "v"}


########################################################################
#                       INFERRED-TERMINATOR ATTRS                      #
########################################################################
class TestInferredTerminator:
  """Specs with ``attribute_terminator=None`` fall back to using the
  last character of ``open_token`` as the terminator when the literal
  match fails. Covers the common case of allowing
  ``<think foo="bar">`` for a default ``<think>`` spec."""

  @pytest.fixture
  def think_spec(self) -> TagSpec:
    return TagSpec(TagType.THINKING, "<think>", "</think>")

  @pytest.fixture
  def think_parser(self, think_spec) -> TagParser:
    return TagParser([think_spec])

  def test_literal_still_matches_with_empty_attrs(self, think_parser):
    events = _events(think_parser, "<think>plain</think>")
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.tag_type == TagType.THINKING
    assert ev.content == "plain"
    assert ev.attributes == {}
    assert ev.raw_open == "<think>"

  def test_inferred_terminator_parses_attributes(self, think_parser):
    events = _events(think_parser, '<think depth="2" tag=note>body</think>')
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.tag_type == TagType.THINKING
    assert ev.content == "body"
    assert ev.attributes == {"depth": "2", "tag": "note"}
    assert ev.raw_open == '<think depth="2" tag=note>'

  def test_inferred_does_not_match_extended_word(self, think_parser):
    events = _events(think_parser, "the word <thinking> is fine")
    assert len(events) == 1
    assert isinstance(events[0], TextEvent)
    assert events[0].text == "the word <thinking> is fine"

  def test_inferred_does_not_match_when_no_separator(self, think_parser):
    events = _events(think_parser, "<thinkX>not a tag")
    assert len(events) == 1
    assert isinstance(events[0], TextEvent)
    assert events[0].text == "<thinkX>not a tag"

  def test_inferred_partial_at_chunk_boundary(self, think_parser):
    events = _events(think_parser, "<think dep", "th=2>body</think>")
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.attributes == {"depth": "2"}
    assert ev.content == "body"

  def test_inferred_skipped_for_single_char_open_token(self):
    spec = TagSpec(TagType.TOOL, "<", "</")
    parser = TagParser([spec])
    events = _events(parser, "<a>hello</")
    types = [type(ev).__name__ for ev in events]
    assert "TagEvent" in types
    tags = [ev for ev in events if isinstance(ev, TagEvent)]
    assert tags[0].content == "a>hello"
    assert tags[0].attributes == {}
    assert tags[0].raw_open == "<"

  def test_default_tool_spec_accepts_attributes(self):
    """The default ``[TOOL_CALL]`` spec should also benefit from
    inferred-terminator attribute parsing."""
    parser = TagParser([DEFAULT_TAGS[TagType.TOOL]])
    events = _events(
      parser,
      "[TOOL_CALL name='echo']{}[/TOOL_CALL]",
    )
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.attributes == {"name": "echo"}
    assert ev.content == "{}"


########################################################################
#                          NESTED TAGS                                 #
########################################################################
class TestNesting:
  def test_simple_nesting_lifo(self, parser):
    text = "<think>outer [TOOL_CALL]inner[/TOOL_CALL] tail</think>"
    events = _events(parser, text)
    assert len(events) == 2
    inner, outer = events
    assert isinstance(inner, TagEvent)
    assert inner.tag_type == TagType.TOOL
    assert inner.content == "inner"
    assert isinstance(outer, TagEvent)
    assert outer.tag_type == TagType.THINKING
    # Outer content includes the entire inner tag verbatim:
    assert outer.content == "outer [TOOL_CALL]inner[/TOOL_CALL] tail"
    assert outer.start_index == 0
    assert outer.end_index == len(text)

  def test_double_nesting(self, parser):
    text = "<think>a<think>b<think>c</think>d</think>e</think>"
    events = _events(parser, text)
    assert len(events) == 3
    assert [ev.content for ev in events] == [
      "c",
      "b<think>c</think>d",
      "a<think>b<think>c</think>d</think>e",
    ]


########################################################################
#                          ERROR EVENTS                                #
########################################################################
class TestParseErrors:
  def test_mismatched_close_inside_tag_emits_error(self, parser):
    text = "<think>some [/TOOL_CALL] stuff</think>"
    events = _events(parser, text)
    errors = [ev for ev in events if isinstance(ev, ParseError)]
    tags = [ev for ev in events if isinstance(ev, TagEvent)]
    assert len(errors) == 1
    assert errors[0].reason == "mismatched_close"
    assert errors[0].got == "[/TOOL_CALL]"
    assert errors[0].expected == "</think>"
    assert len(tags) == 1
    assert tags[0].tag_type == TagType.THINKING
    # The mismatched close text remains part of the outer content.
    assert tags[0].content == "some [/TOOL_CALL] stuff"

  def test_unclosed_at_flush_emits_error(self, parser):
    events = _events(parser, "<think>unfinished business")
    errors = [ev for ev in events if isinstance(ev, ParseError)]
    assert len(errors) == 1
    assert errors[0].reason == "unclosed_tags"
    assert errors[0].expected == "</think>"
    # No TagEvent emitted; the tag was never closed.
    assert not any(isinstance(ev, TagEvent) for ev in events)

  def test_multiple_unclosed_at_flush(self, parser):
    events = _events(parser, "<think>outer<think>inner")
    errors = [ev for ev in events if isinstance(ev, ParseError)]
    # Two unclosed THINKING tags => two errors.
    assert len(errors) == 2
    assert all(e.reason == "unclosed_tags" for e in errors)

  def test_close_in_freestanding_text_is_just_text(self, parser):
    """Close tokens encountered when the stack is empty are plain text."""
    events = _events(parser, "stray [/TOOL_CALL] text")
    assert len(events) == 1
    assert isinstance(events[0], TextEvent)
    assert events[0].text == "stray [/TOOL_CALL] text"


########################################################################
#                       CHUNK BOUNDARY HANDLING                        #
########################################################################
class TestChunkBoundaries:
  @pytest.fixture
  def attr_specs(self) -> List[TagSpec]:
    return [
      TagSpec(
        tag_type=TagType.REFERENCE,
        open_token="<reference",
        close_token="</reference>",
        attribute_terminator=">",
      ),
      TagSpec(
        tag_type=TagType.THINKING,
        open_token="<think>",
        close_token="</think>",
      ),
      TagSpec(
        tag_type=TagType.TOOL,
        open_token="[TOOL_CALL]",
        close_token="[/TOOL_CALL]",
      ),
    ]

  @pytest.fixture
  def fixture_text(self) -> str:
    return (
      "before [TOOL_CALL]hi[/TOOL_CALL] mid "
      '<reference guid="x">refbody</reference> tail'
    )

  def _expected_events(self, fixture_text: str, attr_specs):
    parser = TagParser(attr_specs)
    return _events(parser, fixture_text)

  def test_split_at_every_position(self, attr_specs, fixture_text):
    """Split the fixture at every legal byte boundary and verify the
    event stream is identical to the unsplit baseline."""
    expected = self._expected_events(fixture_text, attr_specs)
    expected_serialized = _serialize(expected)
    for split in range(1, len(fixture_text)):
      a, b = fixture_text[:split], fixture_text[split:]
      parser = TagParser(attr_specs)
      events = _events(parser, a, b)
      assert _serialize(events) == expected_serialized, (
        f"event mismatch when splitting at {split}: "
        f"{events!r} != {expected!r}"
      )

  def test_split_one_char_at_a_time(self, attr_specs, fixture_text):
    parser = TagParser(attr_specs)
    events: List[ParseEvent] = []
    for ch in fixture_text:
      events.extend(parser.feed(ch))
    events.extend(parser.flush())
    expected = self._expected_events(fixture_text, attr_specs)
    assert _serialize(events) == _serialize(expected)

  def test_split_inside_attribute_region(self, attr_specs):
    parser = TagParser(attr_specs)
    events = _events(
      parser,
      '<reference gui',
      'd="x">content</reference>',
    )
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.attributes == {"guid": "x"}
    assert ev.content == "content"


########################################################################
#                         PARSER VALIDATION                            #
########################################################################
class TestParserValidation:
  def test_duplicate_tag_type_rejected(self):
    spec_a = TagSpec(TagType.TOOL, "[A]", "[/A]")
    spec_b = TagSpec(TagType.TOOL, "[B]", "[/B]")
    with pytest.raises(ValueError):
      TagParser([spec_a, spec_b])

  def test_no_specs_yields_only_text(self):
    parser = TagParser([])
    events = _events(parser, "anything goes [TOOL_CALL] here")
    assert len(events) == 1
    assert isinstance(events[0], TextEvent)
    assert events[0].text == "anything goes [TOOL_CALL] here"


########################################################################
#                       SPEC RESOLUTION                                #
########################################################################
class TestResolveTagSpecs:
  def test_returns_defaults_for_none(self):
    specs = resolve_tag_specs(None)
    assert {s.tag_type for s in specs} == set(DEFAULT_TAGS.keys())

  def test_returns_defaults_when_no_overrides(self):
    md = SimpleNamespace()
    specs = resolve_tag_specs(md)
    assert specs == list(DEFAULT_TAGS.values())

  def test_override_replaces_default(self):
    custom = TagSpec(TagType.TOOL, "<<TOOL>>", "<</TOOL>>")
    md = SimpleNamespace(tag_overrides={TagType.TOOL: custom})
    specs = resolve_tag_specs(md)
    types = {s.tag_type: s for s in specs}
    assert types[TagType.TOOL] == custom
    assert types[TagType.THINKING] == DEFAULT_TAGS[TagType.THINKING]

  def test_override_can_introduce_new_tag_type(self):
    extra = TagSpec(TagType.REFERENCE, "<ref>", "</ref>")
    md = SimpleNamespace(tag_overrides={TagType.REFERENCE: extra})
    specs = resolve_tag_specs(md)
    types = {s.tag_type: s for s in specs}
    assert types[TagType.REFERENCE] == extra

  def test_empty_override_map_returns_defaults(self):
    md = SimpleNamespace(tag_overrides={})
    specs = resolve_tag_specs(md)
    assert specs == list(DEFAULT_TAGS.values())

  def test_override_does_not_mutate_defaults(self):
    """Resolving with an override must not leak into ``DEFAULT_TAGS``."""
    snapshot = dict(DEFAULT_TAGS)
    custom = TagSpec(TagType.TOOL, "<<TOOL>>", "<</TOOL>>")
    md = SimpleNamespace(tag_overrides={TagType.TOOL: custom})
    resolve_tag_specs(md)
    assert DEFAULT_TAGS == snapshot

  def test_resolution_then_parsing_uses_overrides(self):
    """End-to-end: a model with custom tokens parses its own format."""
    custom = TagSpec(TagType.TOOL, "<<TOOL>>", "<</TOOL>>")
    md = SimpleNamespace(tag_overrides={TagType.TOOL: custom})
    parser = TagParser(resolve_tag_specs(md))
    events = _events(parser, "<<TOOL>>{}<</TOOL>>")
    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TagEvent)
    assert ev.tag_type == TagType.TOOL
    assert ev.raw_open == "<<TOOL>>"
    assert ev.raw_close == "<</TOOL>>"


########################################################################
#                  RESOLUTION ON CONCRETE ModelDefinition              #
########################################################################
class TestResolveTagSpecsModelDefinition:
  """End-to-end coverage that ``ModelDefinition`` carries
  ``tag_overrides`` correctly through the resolver. These tests prove
  the resolver works against an actual ``ModelDefinition`` and not
  just a duck-typed stand-in."""

  def test_default_definition_has_no_overrides(self):
    from claia.core.definitions.model_definition import ModelDefinition
    md = ModelDefinition()
    assert md.tag_overrides is None
    specs = resolve_tag_specs(md)
    assert specs == list(DEFAULT_TAGS.values())

  def test_definition_with_override_is_applied(self):
    from claia.core.definitions.model_definition import ModelDefinition
    custom = TagSpec(
      tag_type=TagType.TOOL,
      open_token="<tool_call>",
      close_token="</tool_call>",
    )
    md = ModelDefinition(
      title="custom-tool-format",
      tag_overrides={TagType.TOOL: custom},
    )
    specs = resolve_tag_specs(md)
    types = {s.tag_type: s for s in specs}
    assert types[TagType.TOOL] == custom
    # Other tag types remain at their defaults
    assert types[TagType.THINKING] == DEFAULT_TAGS[TagType.THINKING]
    assert types[TagType.REFERENCE] == DEFAULT_TAGS[TagType.REFERENCE]

  def test_definition_partial_override_leaves_others_at_default(self):
    from claia.core.definitions.model_definition import ModelDefinition
    custom_think = TagSpec(
      tag_type=TagType.THINKING,
      open_token="<reasoning>",
      close_token="</reasoning>",
    )
    md = ModelDefinition(tag_overrides={TagType.THINKING: custom_think})
    specs = resolve_tag_specs(md)
    types = {s.tag_type: s for s in specs}
    assert types[TagType.THINKING] == custom_think
    assert types[TagType.TOOL] == DEFAULT_TAGS[TagType.TOOL]
    assert types[TagType.REFERENCE] == DEFAULT_TAGS[TagType.REFERENCE]

  def test_definition_full_override_for_every_tag_type(self):
    from claia.core.definitions.model_definition import ModelDefinition
    overrides = {
      TagType.TOOL: TagSpec(TagType.TOOL, "<<T>>", "<</T>>"),
      TagType.THINKING: TagSpec(TagType.THINKING, "<<R>>", "<</R>>"),
      TagType.REFERENCE: TagSpec(TagType.REFERENCE, "<<X>>", "<</X>>"),
    }
    md = ModelDefinition(tag_overrides=overrides)
    specs = resolve_tag_specs(md)
    types = {s.tag_type: s for s in specs}
    for tag_type, spec in overrides.items():
      assert types[tag_type] == spec
    # No leftover default specs after a full override.
    assert len(specs) == len(overrides)


########################################################################
#                          HELPERS                                     #
########################################################################
def _serialize(events: List[ParseEvent]) -> List[tuple]:
  """Serialize events to tuples for stable equality comparison."""
  out = []
  for ev in events:
    if isinstance(ev, TextEvent):
      out.append(("text", ev.text, ev.start_index, ev.end_index))
    elif isinstance(ev, TagEvent):
      out.append((
        "tag",
        ev.tag_type,
        ev.content,
        tuple(sorted(ev.attributes.items())),
        ev.start_index,
        ev.end_index,
        ev.raw_open,
        ev.raw_close,
      ))
    elif isinstance(ev, ParseError):
      out.append(("err", ev.reason, ev.position, ev.expected, ev.got))
    else:  # pragma: no cover - defensive
      raise AssertionError(f"unknown event type: {ev!r}")
  return out

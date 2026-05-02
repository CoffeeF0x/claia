# Parsers

Streaming, stateful tag-extraction for assistant content.

## What lives here

- `types.py` — `TagType`, `TagSpec`, and the parser's event dataclasses
  (`TextEvent`, `TagEvent`, `ParseError`, plus the `ParseEvent` union).
- `attributes.py` — small state machine that parses the
  `key=value` region between an open prefix and its terminator.
- `streaming.py` — `StreamingTagParser`, the streaming state machine
  that consumes chunks and yields parse events.
- `defaults.py` — `DEFAULT_TAGS`, the one-spec-per-`TagType` global
  default registry.
- `resolution.py` — `resolve_tag_specs(model_def)`, which merges the
  defaults with any per-model `tag_overrides`.

## How parsers fit in

A parser is **per turn**. The agent loop constructs a
`StreamingTagParser` from the active `TagSpec` list (typically
`resolve_tag_specs(model_def)`), then drives it with model output as
it streams:

```python
from claia.core.parsers import StreamingTagParser, TagType, resolve_tag_specs

parser = StreamingTagParser(resolve_tag_specs(model_def))
for chunk in deployment.run(...):
  for ev in parser.feed(chunk.text):
    handle(ev)
for ev in parser.flush():
  handle(ev)
```

The parser is generic — it does not know what tools, thinking, or
references are. It only finds tagged spans. Per-tag-type semantics
(JSON decoding for `TOOL`, structured logging for `THINKING`, etc.)
are the consumer's responsibility.

## TagSpec interpretation

| `attribute_terminator` | `open_token` semantics                                                                                       | Example                                |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------- |
| `None`                 | Full opening literal first; if the literal does not match and `len(open_token) > 1`, falls back to inferring | `[TOOL_CALL]`, `<think>`               |
|                        | the terminator from the token's last character. See "Inferred terminator" below.                             |                                        |
| set (e.g. `]`, `>`)    | Opening **prefix**; whitespace + `key=value` pairs are tolerated up to the terminator.                       | `[TOOL_CALL` … `]`, `<reference` … `>` |

### Inferred terminator (`attribute_terminator=None`, `len > 1`)

A spec like `TagSpec(TagType.THINKING, "<think>", "</think>")` is
matched in two steps:

1. **Literal match.** If `open_token` matches verbatim at the
   current position the parser uses it directly with empty
   attributes (e.g., `<think>` → `attrs={}`).
2. **Inferred-terminator fallback.** Otherwise the parser treats
   `open_token[:-1]` as a prefix (`<think`) and `open_token[-1]` as
   the terminator (`>`), and parses an attribute region between
   them. The character immediately after the prefix must be either
   the terminator or whitespace — `<think foo="x">` matches,
   `<thinking>` does not.

This makes attribute-bearing variants of common tags work without
changing existing default `TagSpec` declarations.

### Attribute syntax (inside the region)

- whitespace-separated `key=value` pairs
- `value` may be `"…"`, `'…'`, or unquoted (no whitespace,
  terminator ends it)
- a bare `key` with no `=` binds to an empty string
- keys are alphanumerics + underscore + dot (XML-like leniency)

## Streaming and partial matches

The parser holds back any input that might still be part of a tag.
At a chunk boundary that lands inside an open prefix, an attribute
region, or a close-token prefix, no event is emitted for the tail of
the chunk; the next `feed()` resumes scanning from the same buffer
position.

`flush()` is called once at end-of-stream. It emits any pending
`TextEvent` outside open tags and a `ParseError` for each unclosed
tag still on the stack.

## Errors

Errors are surfaced **in-band** as `ParseError` events. Consumers
that don't care can ignore them. Two kinds are produced today:

- `reason="mismatched_close"` — a recognized close token was
  encountered that does not match the top of the open-tag stack. The
  token is consumed as plain content and the stack is unchanged.
- `reason="unclosed_tags"` — emitted by `flush()` for each tag still
  open at end-of-stream.

## Constraints

- One spec per `TagType`. The constructor rejects duplicates.
- Two specs whose open tokens prefix-match each other (e.g.,
  `[TOOL_CALL]` and `[TOOL_CALL`) cannot both be active. With one
  default per `TagType` and override-by-replacement, this is not
  encountered in practice.
- Tag content is delivered verbatim. Nested tags are scanned for
  inside content; opaque-content tags are not yet supported (see the
  plan's §12.7 for the future flag).

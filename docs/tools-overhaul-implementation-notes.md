# Tools Subsystem Overhaul — Implementation Notes

This document is the running log of concrete changes made while
implementing the plan in `tools-overhaul-plan.md`. It complements the
plan document: the plan describes intent and design decisions; this
file records what was actually built, where it lives in the tree, and
any deviations from the plan or follow-up items discovered during
implementation.

Keep entries short and grouped by phase. When the implementation
deviates from the plan, note both the deviation and its reason. When a
follow-up surfaces (TODO or open question that wasn't anticipated in
the plan's §12 Open considerations), add it to the
"Follow-ups & deferred items" section at the bottom.

---

## Phase 1 — Parser core

Goal (per plan §11): Stand up the streaming tag parser package
(`claia.core.parsers`) implementing §3 in full, with test coverage for
the cases listed in the phase plan.

### Files added

- `src/claia/core/parsers/__init__.py` — public surface (re-exports of
  `TagType`, `TagSpec`, `TextEvent`, `TagEvent`, `ParseError`,
  `ParseEvent`, `StreamingTagParser`, `DEFAULT_TAGS`,
  `resolve_tag_specs`).
- `src/claia/core/parsers/types.py` — `TagType` enum, `TagSpec`
  dataclass, and the `TextEvent` / `TagEvent` / `ParseError` event
  dataclasses plus the `ParseEvent` union alias.
- `src/claia/core/parsers/attributes.py` — small state-machine for
  parsing the attribute region between an open prefix and the
  attribute terminator (handles `key="…"`, `key='…'`,
  unquoted values, and bare `key` with no value). Exposes
  `parse_attribute_region(buffer, start, terminator)` returning a
  three-state result: complete, partial, or malformed.
- `src/claia/core/parsers/streaming.py` — `StreamingTagParser` with
  `feed(chunk)` and `flush()` generators. Maintains a buffer, a scan
  cursor, a pending-text start, and a LIFO stack of open tags. Uses
  `attributes.parse_attribute_region` for prefix-style opens.
- `src/claia/core/parsers/defaults.py` — `DEFAULT_TAGS` mapping
  `TagType -> TagSpec`. Default tokens follow the suggestions in
  plan §3.3 (`[TOOL_CALL]`/`[/TOOL_CALL]`, `<think>`/`</think>`,
  `[REF]`/`[/REF]`).
- `src/claia/core/parsers/resolution.py` — `resolve_tag_specs(model_def)`
  helper. Reads `model_def.tag_overrides` defensively via `getattr`
  so it works before Phase 2 lands the actual field on
  `ModelDefinition`. Per-`TagType` replacement, no field-level
  merging (plan §3.7).
- `src/claia/core/parsers/README.md` — package overview and usage
  notes.
- `src/tests/core/test_parsers.py` — Phase 1 parser tests covering
  the cases enumerated in plan §11 Phase 1.

### Files modified

- `docs/tools-overhaul-plan.md` — added a pointer to this notes file
  in the introduction so readers know to consult it for as-built
  details.

### Decisions confirmed during implementation

- **`ParseError` shape (plan §12.1).** Adopted the recommendation: a
  third event type in the `ParseEvent` union with fields
  `(reason, position, expected, got)`. Currently emitted with
  `reason="mismatched_close"` for unmatched close tokens encountered
  inside a tag, and `reason="unclosed_tags"` from `flush()` when the
  stack is non-empty at end of stream. Consumers may ignore the
  events; they do not interrupt the iterator.
- **Mismatched-close detection.** When the stack is non-empty the
  parser scans for both the top tag's close token *and* close tokens
  of any other active spec. A non-top close emits a
  `ParseError(reason="mismatched_close")` and is then consumed as
  content (the stack is unchanged). When the stack is empty the
  parser does **not** scan for close tokens — they are plain text.
- **No buffer dropping in v1.** The parser keeps the full conceptual
  stream in `_buffer`. Absolute event positions are simply buffer
  indices. `_cursor` from the plan is omitted because there is no
  offset to maintain. If memory pressure becomes a concern for very
  long responses, future work can drop bytes ahead of `_text_start`
  when the stack is empty and reintroduce `_cursor`. See follow-ups.
- **Attribute parsing leniency.** The attribute parser supports
  double-quoted, single-quoted, unquoted (whitespace- or
  terminator-delimited), and bare-key (no `=`) attributes. Bare keys
  bind to an empty string. Keys are restricted to alphanumerics,
  underscore, and dot.
- **Spec validation.** The `StreamingTagParser` constructor rejects
  duplicate `TagType` entries up front, since the rest of the
  algorithm assumes per-type uniqueness (plan §3.3, §3.7).
- **`resolve_tag_specs` signature.** Implemented as the plan
  describes; returns the merged values as a `List[TagSpec]` so it can
  be passed straight into `StreamingTagParser`. Phase 2 will add the
  `tag_overrides` field on `ModelDefinition` and proper unit tests
  for merging.

### Deviations from the plan

- None of substance in this phase. All deviations are described inline
  above (e.g., omitting `_cursor` because the buffer is not dropped).

### Test coverage added

`src/tests/core/test_parsers.py` covers:

- text-only stream (no tags) flushes correctly
- simple non-attributed tag spans with absolute indices
- text events between tags
- attributed tags in XML style (`<reference guid="x">…</reference>`)
- attributed tags in bracket style
  (`[TOOL_CALL NAME='do_thing']…[/TOOL_CALL]`)
- attributes with single quotes, double quotes, unquoted values, and
  bare-key (missing value)
- nested tags in strict LIFO order
- mismatched close tokens emit a `ParseError` and the stream
  continues
- non-empty stack at flush emits a `ParseError`
- chunk boundaries at every byte position of a representative
  fixture (parametrized)
- attribute region split across chunk boundaries

---

## Follow-ups & deferred items

These are items discovered during implementation that were not
explicit in the plan's §12 Open considerations. Resolve in a later
phase or follow-up.

- **Buffer growth.** The v1 parser never drops consumed bytes from
  its buffer. For multi-MB streams this could become a concern. A
  future change can drop everything before `_text_start` when the
  stack is empty (and update positions through a `_cursor` offset
  the way the plan originally described).

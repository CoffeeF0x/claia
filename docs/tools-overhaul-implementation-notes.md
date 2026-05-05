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
(`claia.core.parser`) implementing §3 in full, with test coverage for
the cases listed in the phase plan.

### Files added

- `src/claia/core/parser/__init__.py` — public surface (re-exports of
  `TagType`, `TagSpec`, `TextEvent`, `TagEvent`, `ParseError`,
  `ParseEvent`, `TagParser`, `DEFAULT_TAGS`,
  `resolve_tag_specs`).
- `src/claia/core/parser/types.py` — `TagType` enum, `TagSpec`
  dataclass, and the `TextEvent` / `TagEvent` / `ParseError` event
  dataclasses plus the `ParseEvent` union alias.
- `src/claia/core/parser/utils.py` — `parse_attribute_region` for the
  attribute region after an open prefix, plus `OpenTag`, `KEY_CHARS` /
  `WHITESPACE`, and `is_proper_prefix`.
- `src/claia/core/parser/tag_parser.py` — `TagParser` with
  `feed(chunk)` and `flush()` generators. Maintains a buffer, a scan
  cursor, a pending-text start, and a LIFO stack of open tags. Uses
  `parse_attribute_region` for prefix-style opens.
- `src/claia/core/parser/defaults.py` — `DEFAULT_TAGS` mapping
  `TagType -> TagSpec`. Default tokens follow the suggestions in
  plan §3.3 (`[TOOL_CALL]`/`[/TOOL_CALL]`, `<think>`/`</think>`,
  `[REF]`/`[/REF]`).
- `src/claia/core/parser/resolution.py` — `resolve_tag_specs(model_def)`
  helper. Reads `model_def.tag_overrides` defensively via `getattr`
  so it works before Phase 2 lands the actual field on
  `ModelDefinition`. Per-`TagType` replacement, no field-level
  merging (plan §3.7).
- `src/claia/core/parser/README.md` — package overview and usage
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
- **Spec validation.** The `TagParser` constructor rejects
  duplicate `TagType` entries up front, since the rest of the
  algorithm assumes per-type uniqueness (plan §3.3, §3.7).
- **`resolve_tag_specs` signature.** Implemented as the plan
  describes; returns the merged values as a `List[TagSpec]` so it can
  be passed straight into `TagParser`. Phase 2 will add the
  `tag_overrides` field on `ModelDefinition` and proper unit tests
  for merging.
- **Inferred terminator for `attribute_terminator=None`.** Extension
  to plan §3.4: when `attribute_terminator is None` and
  `len(open_token) > 1`, the parser still tries the verbatim literal
  match first, then falls back to interpreting `open_token[-1]` as
  the terminator and `open_token[:-1]` as the prefix. The fallback
  requires the character immediately after the prefix to be either
  the inferred terminator or whitespace, which prevents
  unintended matches like `<thinking>` against `<think>`. This makes
  attribute-bearing variants of common tags (e.g.,
  `<think depth="2">…</think>`,
  `[TOOL_CALL name='echo']…[/TOOL_CALL]`) work without forcing every
  spec to declare an explicit terminator. The behavior change is
  additive: any existing literal-only match continues to match
  unchanged.

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

## Phase 2 — Tag specs in model definitions

Goal (per plan §11): Expose `tag_overrides` on `ModelDefinition`
and ensure `resolve_tag_specs` reads the real field end-to-end,
with merge-aware behavior in the framework's definition merger.

### Files modified

- `src/claia/core/definitions/model_definition.py` — added the
  `tag_overrides: Optional[Dict[TagType, TagSpec]] = None` field and
  imported `TagSpec`/`TagType` from `claia.core.parser.types`. Kept
  the field default `None` so existing callers and persisted data
  need no migration. Documented the field on the class docstring
  per plan §3.7 (per-`TagType` replacement, no field-level merging).
- `src/claia/framework/manager.py` — `Manager.get_supported_models`
  now propagates `tag_overrides` through the cross-provider merge
  path. Added a private `_merge_tag_overrides(existing, incoming)`
  helper that mirrors the existing list/dict mergers: last-wins on
  `TagType` keys, returns `None` when both sides are empty.
- `src/claia/core/parser/resolution.py` — refreshed the module
  docstring now that the field is a real attribute on
  `ModelDefinition` rather than a Phase 2 placeholder. The
  `getattr(model_def, "tag_overrides", None)` lookup is retained so
  duck-typed stand-ins (e.g., test fixtures) still work.
- `src/tests/core/test_parsers.py` — added `TestResolveTagSpecs`
  cases for empty override maps and immutability of `DEFAULT_TAGS`,
  plus end-to-end `TestResolveTagSpecsModelDefinition` covering the
  resolver against a concrete `ModelDefinition`, plus
  `TestModelDefinitionTagOverridesMerge` covering the manager's
  `_merge_tag_overrides` helper directly.

### Decisions confirmed during implementation

- **Override merge semantics.** Per plan §3.7 there is no field-level
  merging within a `TagSpec`; the `Manager` merger therefore performs
  per-`TagType` replacement (last definition wins). This matches the
  intent of "if a model overrides `TagType.TOOL`, it provides a
  complete `TagSpec`."
- **Defensive `getattr` retained in `resolve_tag_specs`.** Even
  though `ModelDefinition` now owns the field, the resolver still
  uses `getattr(..., "tag_overrides", None)` so callers can pass
  duck-typed stand-ins (existing tests use `SimpleNamespace`). The
  dependency direction is parser → definitions only via
  `claia.core.parser.types`, which is import-safe (parser types
  module imports only from stdlib).
- **No native definitions ship overrides yet.** The plan allows
  "Update existing model definitions (or leave at default)"; we
  leave the legacy/openai/anthropic/openrouter providers at the
  defaults. As models that emit non-default delimiters are added
  (e.g., providers that use `<tool_call>`), they can opt in by
  setting `tag_overrides`.

### Deviations from the plan

- None of substance. The plan's Phase 2 description is fully
  realized; the resolver was already written defensively in Phase 1
  so only the field, docstrings, and merge path needed updating.

### Test coverage added

- `test_empty_override_map_returns_defaults` — `tag_overrides={}` is
  treated as no-overrides.
- `test_override_does_not_mutate_defaults` — `DEFAULT_TAGS` is
  preserved across resolver calls.
- `test_resolution_then_parsing_uses_overrides` — end-to-end:
  resolved specs drive a real `TagParser` that recognizes the
  overridden delimiters.
- `TestResolveTagSpecsModelDefinition` — concrete `ModelDefinition`
  with no overrides, with one override, with a partial-set override,
  and with overrides for every `TagType` (default specs disappear
  when fully replaced).
- `TestModelDefinitionTagOverridesMerge` — `_merge_tag_overrides`
  with neither, only-existing, only-incoming, disjoint keys, and
  conflict resolution; also asserts inputs are not mutated.

---

## Phase 3 — Message + Conversation extensions

Goal (per plan §11): introduce the `UTILITY` role and the
sibling-utility-message data model on `Message` /
`Conversation` so parsed tag spans (tool calls, thinking blocks,
references) can live as first-class messages alongside the
assistant text they were extracted from.

### Files modified

- `src/claia/core/enums/conversation.py` — added
  `MessageRole.UTILITY = "utility"` with class-docstring
  documentation pointing back to plan §2.4 / §4. The dead
  `TagType` / `TagStatus` enums in this same module are left in
  place for now; they have zero importers and will be cleaned up
  in a later phase (likely Phase 7's pattern-subsystem removal,
  which is the natural place to retire the legacy tag types).
- `src/claia/core/data/models/conversation/message.py` — added
  optional `tag_type` / `source_message_id` / `start_index` /
  `end_index` / `attributes` fields to `Message.__init__` (each
  defaulting to `None` / `{}`); `tag_type` is coerced from its
  string `value` form to support deserialization. New `is_utility()`
  helper. `to_dict` now omits unset utility fields so legacy
  user/assistant messages serialize byte-for-byte unchanged from
  earlier versions; `from_dict` reads the new fields with
  defaults so payloads written before Phase 3 deserialize without
  modification. Imports `TagType` from
  `claia.core.parser.types` (the parser's categorical enum, not
  the legacy `claia.core.enums.conversation.TagType`).
- `src/claia/core/data/models/conversation/conversation.py` —
  - `get_thread(head_id=None, include_utility=False)` filters
    `MessageRole.UTILITY` messages out of the linearized thread by
    default. Pass `include_utility=True` to surface them (UI,
    debug, replay).
  - `get_messages(speaker=None, include_utility=False)` mirrors
    the same flag and additionally surfaces utility messages
    automatically when the caller's `speaker` filter explicitly
    asks for `MessageRole.UTILITY`.
  - New `append_utility(tag_type, content, source_message_id, …)`
    method: constructs a `Message` with `role=UTILITY` and the
    utility fields populated, appends it to `self.messages`,
    advances `active_head_id` so further turns chain
    chronologically, and emits a `MESSAGE_CREATED` domain event
    with `tag_type` / `source_message_id` / index metadata. It
    intentionally bypasses `extract_inline_args` so JSON-shaped
    tag bodies round-trip verbatim.
- `src/tests/core/test_utility_messages.py` — new Phase 3 test
  module with 24 tests covering enum membership, message
  construction (including string-form `tag_type` coercion and
  attribute aliasing), serialization round-trip, legacy-payload
  compatibility, `Conversation.append_utility` semantics
  (head advancement, event emission, parent_id override,
  inline-arg bypass), `get_thread` / `get_messages` filtering,
  and full `Conversation` round-trip via both `to_dict`/`from_dict`
  and the JSON `set_content` path.

### Decisions confirmed during implementation

- **`tag_type` typing.** `Message.tag_type` carries
  `claia.core.parser.types.TagType` (the categorical "tool" /
  "thinking" / "reference" enum from Phase 1), not the dead
  `TagType` enum still sitting in
  `claia.core.enums.conversation` (which encodes literal token
  strings). The constructor accepts the string `.value` form so
  serialized payloads round-trip, and the dead enum is left
  untouched until a dedicated cleanup phase.
- **Backwards compatibility on the wire.** `to_dict` only
  emits utility fields when they are non-default. This means
  every conversation persisted before Phase 3 serializes
  identically (verified by
  `test_legacy_payload_round_trip_unchanged` and
  `test_legacy_conversation_round_trip_unchanged`). New
  utility-bearing payloads carry the additional keys; older
  consumers that ignore unknown keys keep working.
- **Tree placement of utility messages.** `append_utility`
  defaults the new message's `parent_id` to the current
  `active_head_id` (chronological chaining behind the source
  assistant or the previous utility), and `source_message_id`
  is stored as an explicit, separate field. This matches plan
  §2.4 ("siblings, not children" of the assistant message in
  the flat list, while the explicit `source_message_id` link
  remains stable across edits). An explicit `parent_id`
  parameter is supported for callers that need to anchor a
  utility somewhere other than the active head (e.g. attaching
  retroactively to a buried branch).
- **Inline-arg extraction skipped for utility content.** The
  default `add_message` path runs `Message.extract_inline_args`,
  which would consume `{...}`-shaped JSON payloads and clear
  the utility's content. `append_utility` constructs the
  message directly and appends to `self.messages` without that
  side-effect, guaranteeing tag bodies (especially JSON tool
  calls) survive intact.
- **`get_latest_message` not changed.** That helper looks up
  `active_head_id` directly and only falls back to
  `get_thread()` when the head is missing. Leaving it on the
  raw `messages` map is intentional: the active head can
  legitimately be a utility message after a streamed turn, and
  callers that ask for "the latest message" should see whatever
  was actually last appended. Callers that want a non-utility
  view should request `get_thread()` explicitly.

### Deviations from the plan

- **`append_utility` introduced in Phase 3.** Plan §11's Phase 3
  bullets do not mention this helper; it appears only in plan
  §9's agent-loop pseudocode (Phase 6). Adding it now keeps the
  data-model surface complete in one place and lets Phase 3
  carry its own round-trip tests without reaching into private
  state. Phase 6 will use it as documented.

### Test coverage added

- Enum membership: new `UTILITY` value and uniqueness against
  existing roles.
- Message construction: default-empty utility fields,
  fully-populated utility fields, string-`value` coercion of
  `tag_type`, defensive copying of the `attributes` dict.
- Serialization: full round-trip, `to_dict` omitting unset
  optional fields, `tag_type` serialized to its string `value`,
  legacy-payload deserialization yielding default-empty utility
  fields and re-serializing identically.
- `Conversation.append_utility`: head advancement, default-and-
  explicit `parent_id` placement, JSON-payload survival
  (no inline-arg extraction), event emission with full metadata.
- `get_thread` / `get_messages`: utility filtered by default,
  surfaced via `include_utility=True`, surfaced when speaker
  filter explicitly requests `MessageRole.UTILITY`, and the flat
  `self.messages` list always contains every message regardless
  of linearization filtering.
- Full `Conversation` round-trip via both `to_dict`/`from_dict`
  and the JSON `set_content` path.

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
- **`Manager.get_supported_models` merger drops modality fields.**
  Pre-existing bug independent of Phase 2: when two providers
  contribute a definition with the same name, `input_modalities`
  and `output_modalities` are not propagated through the merged
  `ModelDefinition` and silently revert to the
  `[Modality.TEXT]` default. Phase 2 only added the `tag_overrides`
  case; the modality regression should be fixed in a follow-up
  (likely by switching the merger to a generic field-by-field
  walk over the dataclass fields with merge-rules registered per
  field, instead of the current hand-listed kwargs).
- **Dead `TagType` / `TagStatus` enums in
  `claia.core.enums.conversation`.** These predate the parser
  package and are not imported anywhere; the parser's
  categorical `TagType` (`claia.core.parser.types.TagType`) is
  the live one. Phase 3 deliberately avoided touching them so
  the diff stays tightly scoped to the message-and-conversation
  surface; Phase 7's pattern-subsystem removal is the natural
  place to retire them along with related legacy code paths.

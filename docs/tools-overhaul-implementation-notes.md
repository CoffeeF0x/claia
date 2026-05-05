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
  documentation pointing back to plan §2.4 / §4. Also removed
  the dead `TagType` (literal-token-string enum) and `TagStatus`
  enums living in the same module. They predated the parser
  package, had zero importers in the repo, and would be a
  source of confusion now that the live categorical
  `claia.core.parser.types.TagType` is referenced from
  ``Message``. The `auto` import is also dropped since
  ``MessageRole`` only uses string values.
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
  "thinking" / "reference" enum from Phase 1). The legacy
  literal-token-string `TagType` and the unused `TagStatus`
  that previously lived in
  `claia.core.enums.conversation` were removed in this same
  commit so the parser's enum is unambiguously the source of
  truth. The constructor accepts the string `.value` form so
  serialized payloads round-trip.
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

## Phase 4 — Protocol contract rewrite

Goal (per plan §11): replace the pre-overhaul ``BaseProtocol`` /
``ProtocolHooks`` contract with the new surface described in plan §6:
protocols own their own tool inventory, expose a lifecycle
(``start`` / ``stop`` / ``refresh``), and execute against a raw payload
string. The old contract stays importable with a deprecation banner so
third-party extensions have a grace period to migrate.

### Files added

- ``src/claia/core/tools/protocols/_legacy.py`` — keeps the
  pre-overhaul ABC importable as ``LegacyBaseProtocol``. Imports fire
  a ``DeprecationWarning`` at module-load time and a second one when a
  subclass is created, pointing authors at the new
  ``claia.core.tools.protocols.base.BaseProtocol``.
- ``src/tests/framework/test_protocol_contract.py`` — 37-case phase 4
  regression suite covering ``ToolReference``, the new ABC,
  ``SimpleProtocolPlugin`` under the new contract, the pluggy
  registrar, the hookspec signature, ``Manager`` lifecycle wiring, and
  the ``Registry.refresh_tools`` / ``Registry.shutdown`` surface.

### Files modified

- ``src/claia/core/plugins/base.py`` — added ``ToolReference``
  (``qualified_name`` / ``description`` / ``protocol_name`` /
  ``parameter_schema`` / ``tags``). ``parameter_schema`` is typed
  ``Any`` with a ``None`` default so protocols can return references
  whose argument shape is not JSON-Schema-like (plan §2.10 / §6.1).
- ``src/claia/core/plugins/__init__.py`` — re-export ``ToolReference``
  alongside the existing plugin-info dataclasses.
- ``src/claia/core/tools/protocols/base.py`` — new ``BaseProtocol``
  ABC with:
  - Class-level ``info: ClassVar[ProtocolInfo]`` + default
    ``get_protocol_info`` passthrough.
  - Default no-op ``start`` / ``stop`` / ``refresh`` methods so static
    protocols can subclass without lifecycle boilerplate.
  - Abstract ``get_tool_references() -> List[ToolReference]``.
  - Abstract
    ``execute(qualified_name, raw_payload, conversation, **kwargs) -> Result``.
  The old ``execute(tool_name, parameters, conversation, commands, **kwargs)``
  signature now lives on ``LegacyBaseProtocol``.
- ``src/claia/core/tools/protocols/simple.py`` — ``SimpleProtocolPlugin``
  now inherits from the new ``BaseProtocol``:
  - Adds ``bind_tool_modules(modules)`` as a transitional setter
    (phase 5 will fold this into ``__init__``).
  - ``get_tool_references()`` walks bound modules and emits
    ``ToolReference(qualified_name="<module>.<tool>",
    protocol_name="simple", parameter_schema=<ArgumentDefinition map>)``.
  - ``execute(qualified_name, raw_payload, ...)`` decodes
    ``raw_payload`` as JSON. Both the flat form (``{"key": "value"}``)
    and the envelope form (``{"name": ..., "parameters": {...}}``) are
    accepted; the dispatch target is always ``qualified_name`` as
    supplied by the registry, so a mismatched envelope ``name`` is
    informational.
  - Pre-overhaul logic is preserved verbatim as ``execute_legacy`` so
    ``Registry.process_content`` keeps working during phases 4 – 5.
  - ``_normalize_result`` is now a shared helper used by both paths.
- ``src/claia/framework/hooks/protocol.py`` — hookspec rewritten to
  mirror the new ABC: ``get_protocol_info``, ``start``, ``stop``,
  ``refresh``, ``get_tool_references``, and the new ``execute``
  signature. Also re-exports ``ToolReference`` so ``framework.hooks``
  consumers have a single import point.
- ``src/claia/framework/hooks/__init__.py`` — surfaces ``ToolReference``
  in the framework-hooks namespace.
- ``src/claia/framework/registrars.py`` — ``ProtocolRegistrar`` grew
  ``@hookimpl`` methods for ``start`` / ``stop`` / ``refresh`` /
  ``get_tool_references`` and rewired ``execute`` to the new keyword
  arguments. ``_BaseRegistrar.__getattr__`` keeps delegating unknown
  names to the wrapped plugin, which is how ``Registry.process_content``
  still reaches ``execute_legacy`` during the transition.
- ``src/claia/framework/manager.py``:
  - Added ``_iter_protocol_instances`` (yields the plain plugin
    instances, not their registrar shells) plus ``_start_protocols``,
    ``stop_protocols``, ``refresh_protocols``. Each method logs-and-
    continues on a per-protocol exception so one malfunctioning
    protocol cannot take the rest down.
  - ``load_all_plugins`` now calls ``_start_protocols()`` after the
    tool-group loads complete (plan §11 Phase 4 bullet 5).
- ``src/claia/framework/registry.py``:
  - ``process_content`` switched to ``protocol_plugin.execute_legacy``
    to preserve the current tool-call flow while the new ABC rolls
    out (plan §7.3, transitional shim).
  - Added ``refresh_tools()`` — delegates to
    ``manager.refresh_protocols()`` and invalidates the cached
    commands catalog. Phase 5 replaces the catalog with the unified
    ``_tool_index`` rebuild.
  - Added ``shutdown()`` — combines ``stop_workers`` with
    ``manager.stop_protocols`` for clean teardown of external
    sessions.
- ``src/claia/framework/__init__.py`` — re-export ``ToolReference``.

### Decisions confirmed during implementation

- **Legacy ABC parked under ``_legacy`` rather than the public
  ``base`` module.** The plan calls for the old surface to remain
  "importable under deprecation banner". We chose a new, clearly
  demarcated module (``claia.core.tools.protocols._legacy``) so the
  main ``base`` module can be rewritten cleanly without touching the
  legacy implementation. The legacy module fires a
  ``DeprecationWarning`` twice: once at import (module-level
  ``warnings.warn``) and once at subclass creation (via
  ``__init_subclass__``), so both "just imports the symbol" and
  "builds a plugin against it" paths surface the signal.
- **``BaseProtocol.start`` / ``stop`` / ``refresh`` default to
  no-ops.** Plan §6.2 phrases these as defaults, and the simple
  protocol does not need any of them yet; leaving them concrete on
  the ABC keeps static protocols (simple, any future pure-Python
  bridge) free of mandatory boilerplate. Abstract methods remain
  ``get_tool_references`` and ``execute`` only.
- **``execute_legacy`` kept on ``SimpleProtocolPlugin`` for the
  transition.** The alternative — collapsing the old dispatch into
  the new ``execute`` — would have required phase 5 work (kwarg
  preparation moving out of the registry) earlier than the plan
  sequences it. Keeping the old method accessible through the
  registrar's ``__getattr__`` means ``Registry.process_content`` can
  continue to operate against the prepared-kwargs / commands-catalog
  contract without reaching for the pluggy hook surface. Phase 6
  deletes both the legacy method and the shim together.
- **``SimpleProtocolPlugin.bind_tool_modules`` as a transitional
  setter.** Plan §8.2 describes the simple protocol being
  constructed with its modules in hand at framework startup. Because
  the framework instantiates plugins with no arguments (Manager
  contract), the binding has to land via a follow-up call. Exposing
  ``bind_tool_modules`` now — as opposed to waiting for phase 5 —
  lets us ship the new ``get_tool_references`` / ``execute`` methods
  with realistic behavior and tests today, while leaving the actual
  framework-side wiring (who calls ``bind_tool_modules`` when) to
  phase 5.
- **JSON payload envelope + flat accepted.** Simple protocol's
  ``execute`` handles both ``{"key": "value"}`` and the richer
  ``{"name": ..., "parameters": {...}}``. The envelope form mirrors
  what the parser will hand in once phase 6 lands tool-call payloads
  as ``TagEvent.content``. The flat form is useful for direct tests
  and any tag writer that skips the envelope. The envelope ``name``
  is informational — the registry resolves dispatch via
  ``qualified_name``.
- **Registry ``shutdown`` is idempotent.** It swallows exceptions
  from ``stop_workers`` and ``stop_protocols`` so a partially-broken
  shutdown still progresses. Given how many hosts (CLI, tests,
  future HTTP layer) call shutdown from diverse contexts, keeping
  the method tolerant is more valuable than crashing loudly.

### Deviations from the plan

- **Phase 4 adds ``bind_tool_modules`` and a working ``execute``
  implementation on ``SimpleProtocolPlugin``.** The plan's phase 5
  bullet (``SimpleProtocolPlugin`` "constructed with the loaded
  native tool modules at framework startup") is a strict prerequisite
  for surfacing tools through the new contract. Rather than leave
  ``execute`` / ``get_tool_references`` as stubs until phase 5, we
  shipped a minimal end-to-end path now. The kwarg-prep path + JSON
  schema decoding from the registry still moves in phase 5 per plan;
  this change only anticipates the *binding* step.
- **``ToolReference.parameter_schema`` defaults to ``None``.** The
  plan shows ``parameter_schema`` as a required field; we made it
  optional with a ``None`` default so protocol implementations that
  don't expose argument schemas (e.g. a hypothetical bridge that
  only surfaces name + description) don't have to invent a schema
  shape. This is purely additive — every call site that passes a
  concrete value continues to work.

### Test coverage added

``src/tests/framework/test_protocol_contract.py`` (37 cases):

- ``ToolReference``: required / default fields, opaque
  ``parameter_schema``, non-shared tag lists, re-export through the
  three public surfaces.
- ``BaseProtocol``: abstract-method enforcement,
  ``get_protocol_info`` passthrough, no-op lifecycle defaults.
- Legacy ABC: ``DeprecationWarning`` fires on import and on subclass
  creation.
- ``SimpleProtocolPlugin`` (new ``execute``): empty-inventory
  not-found, qualified-name dispatch, JSON flat and envelope
  payloads, empty payload, invalid JSON, non-object JSON, string
  return wrapped in ``Result.ok``, invalid return flagged, callable
  exception translated to ``Result.fail``, tolerating a broken
  module during inventory walking.
- ``SimpleProtocolPlugin`` (``execute_legacy``): catalog-driven
  dispatch, missing-tool fallback.
- ``ProtocolRegistrar``: all six hooks delegated, execute forwards
  keyword arguments.
- ``ProtocolHooks``: declares the expected hook names and the new
  execute signature.
- ``Manager`` lifecycle: ``start`` fires at load time,
  ``stop_protocols`` / ``refresh_protocols`` iterate every loaded
  protocol, errors from any one protocol are swallowed so the rest
  still run.
- ``Registry``: ``refresh_tools`` no-ops before plugins are loaded,
  delegates to ``manager.refresh_protocols`` and invalidates the
  commands catalog after load; ``shutdown`` calls both
  ``stop_workers`` and ``stop_protocols`` when plugins are loaded
  and skips the latter otherwise.

---

## Phase 5 — Simple protocol rewrite

Goal (per plan §11): split ``SimpleProtocolPlugin`` into a package
that owns its own dispatch (kwarg prep, type coercion, JSON payload
decoding), give ``Registry`` the unified ``_tool_index`` /
``execute_tool`` / ``list_tools`` / ``get_tool`` surface, retire the
old ``_commands_catalog`` cache, and have the ``Manager`` hand
loaded native tool modules to the simple protocol at startup. The
transitional ``process_content`` shim and ``execute_legacy`` callee
both stay alive for phase 6 to retire together.

### Files added

- ``src/claia/core/tools/protocols/simple/__init__.py`` —
  re-exports ``SimpleProtocolPlugin`` so the
  ``simple = "claia.core.tools.protocols.simple:SimpleProtocolPlugin"``
  entry point resolves at the package path unchanged.
- ``src/claia/core/tools/protocols/simple/payload.py`` —
  ``decode_payload(raw_payload) -> (parameters, name_hint)`` accepts
  flat (``{"k": "v"}``) and envelope
  (``{"name": "x", "parameters": {...}}``) JSON shapes; empty input
  is ``({}, None)``; non-JSON / non-object payloads raise
  ``ValueError``. Envelope ``name`` is informational only — dispatch
  still uses the registry-supplied ``qualified_name``.
- ``src/claia/core/tools/protocols/simple/dispatcher.py`` —
  ``convert_type``, ``prepare_command_kwargs``, ``find_tool``, and
  ``normalize_result``. These are the helpers that used to live as
  ``Registry._prepare_command_kwargs`` and ``Registry._convert_type``;
  they're now imported by both ``SimpleProtocolPlugin.execute`` and
  ``Registry.run_command`` so kwarg-prep semantics stay identical
  across both entry points.
- ``src/claia/core/tools/protocols/simple/protocol.py`` —
  ``SimpleProtocolPlugin`` itself: ``bind_tool_modules`` setter, a
  ``bound_modules`` read-only view, ``get_tool_references``,
  ``execute(qualified_name, raw_payload, conversation, **kwargs)``
  delegating into ``payload`` + ``dispatcher``, and
  ``execute_legacy`` preserved for the registry's transitional
  ``process_content`` shim.
- ``src/claia/core/tools/protocols/simple/README.md`` — package
  overview, payload-shape examples, and the ``run_command`` vs
  ``execute_tool`` entry-point split.
- ``src/tests/framework/test_simple_protocol_phase5.py`` — 59-case
  suite covering the new package layout, ``decode_payload`` shapes,
  every dispatcher helper, ``SimpleProtocolPlugin`` integration,
  ``Manager`` binding, and the new ``Registry`` surface.

### Files modified

- ``src/claia/framework/manager.py``:
  - ``load_all_plugins`` now calls a new
    ``_bind_native_tools_to_protocols()`` between the
    ``claia.tool_modules`` load and ``_start_protocols()`` so a
    protocol's ``start()`` can already see its inventory.
  - ``_bind_native_tools_to_protocols`` collects every loaded
    ``BaseToolModule`` instance and calls ``bind_tool_modules`` on
    every protocol that exposes the duck-typed hook (currently only
    ``SimpleProtocolPlugin``). Per-protocol failures log + skip so a
    misbehaving binder cannot block other protocols.
  - Added a public ``iter_protocol_instances()`` that delegates to
    ``_iter_protocol_instances`` so ``Registry._rebuild_tool_index``
    can iterate the loaded protocols without reaching into a
    private accessor.
- ``src/claia/framework/registry.py``:
  - Removed ``_commands_catalog`` cache,
    ``_prepare_command_kwargs``, and ``_convert_type`` per plan §7.4.
  - Added ``_tool_index: Optional[Dict[str, ToolReference]]`` and
    ``_protocols_by_name: Optional[Dict[str, BaseProtocol]]`` plus a
    ``_rebuild_tool_index`` walker that iterates
    ``manager.iter_protocol_instances()`` and applies the
    first-in-list-wins dedupe rule (plan §2.8).
    ``_ensure_tool_index`` lazily builds the index on first use.
  - Added ``list_tools()``, ``get_tool(qualified_name)``, and
    ``execute_tool(qualified_name, raw_payload, conversation, **kwargs)``
    per plan §7.2. ``execute_tool`` resolves through the index,
    routes to ``protocol.execute``, and translates protocol
    exceptions into ``Result.fail``.
  - ``refresh_tools`` invalidates ``_tool_index`` and
    ``_protocols_by_name`` instead of the old commands-catalog
    cache; the next access rebuilds from post-refresh inventories.
  - ``process_content`` and ``run_command`` now import
    ``prepare_command_kwargs`` / ``normalize_result`` from
    ``claia.core.tools.protocols.simple.dispatcher`` instead of
    using private registry methods. ``process_content`` keeps its
    ``execute_legacy`` dispatch path; ``run_command`` performs its
    own lookup + prep + invoke + normalize chain because CLI
    parameter dicts contain non-JSON-serializable Python objects
    (``registry``, ``command_specs``, etc.) that must reach the
    callable without a JSON round-trip (plan §7.4 second bullet).
  - ``get_commands_catalog`` survives as a transitional accessor
    that delegates straight to ``manager.get_all_commands()`` —
    no caching — so the surviving ``process_content`` shim and any
    legacy introspectors keep working until phase 6 retires them.
- ``src/tests/framework/test_protocol_contract.py`` — Phase 4
  registry-refresh test updated to assert on the new
  ``_tool_index`` / ``_protocols_by_name`` invalidation instead of
  the now-removed ``_commands_catalog`` cache.

### Files removed

- ``src/claia/core/tools/protocols/simple.py`` — replaced by the
  package of the same name.

### Decisions confirmed during implementation

- **Manager binds native tools via duck-typing.** Plan §8.2 calls
  out the simple protocol specifically, but hard-coding "simple" in
  the manager would prevent third-party protocols (e.g. a hosted
  RPC bridge) from opting into the same native-module surface.
  ``_bind_native_tools_to_protocols`` therefore checks for a
  ``bind_tool_modules`` attribute on each protocol instance instead
  of dispatching by name. Single-arg signature (``modules``) keeps
  the contract narrow.
- **``run_command`` stays on the registry, doesn't go through
  ``execute_tool``.** Plan §7.4 allows either approach; the deciding
  factor was the in-tree CLI commands (e.g.
  ``cli/commands/system.py:HelpCommand``) that pass non-JSON-
  serializable Python objects (``registry``, ``command_specs``)
  inside ``parameters``. Routing those through ``execute_tool``
  would require JSON-encoding ``parameters``, which would either
  break those callers or force them to split injectables out of
  ``parameters``. Phase 5 keeps ``run_command`` on the registry,
  using the same ``dispatcher`` helpers as the protocol so kwarg-
  prep stays consistent. Phase 6 (or a follow-up) can revisit the
  CLI-side split.
- **Inventory rebuild is lazy.** ``_rebuild_tool_index`` runs the
  first time ``list_tools`` / ``get_tool`` / ``execute_tool`` is
  called after load (or after ``refresh_tools``). This keeps
  ``Registry.__init__`` free of the cross-protocol walk so the
  cheap "construct then ask for ParamSpecs" startup path used by
  ``Settings`` doesn't pay for the dispatch index it doesn't need.
- **First-in-list-wins on duplicates.** Implemented exactly as plan
  §2.8 prescribes — pluggy load order determines precedence; the
  collision is logged at ``DEBUG`` and the late-arriving entry
  drops out. A future protocol that wants explicit precedence will
  need an explicit ``priority`` field, deferred per plan §12.8.
- **``get_commands_catalog`` no longer caches.** The previous
  caching wasn't safe across ``refresh_tools`` cycles anyway; phase
  5 makes the helper a thin call into ``manager.get_all_commands``
  so the legacy shim always sees fresh data. The new ``_tool_index``
  is the post-overhaul cache and lives at a different abstraction
  level.
- **Legacy dispatch (``execute_legacy``) is the only place
  ``commands`` catalogs still flow.** The new ``execute`` path
  takes only ``raw_payload`` + ``conversation`` + ``**kwargs``; the
  catalog is internal to the protocol via the bound modules. Plan
  §7.3's "transitional shim retained for one phase" applies to the
  surface ``process_content`` exposes; phase 6 deletes both pieces.

### Deviations from the plan

- **``_tool_index`` is built lazily, not "after protocols load".**
  Plan §7.1 implies eager assembly during ``load_all_plugins``;
  phase 5 deferred to first use. Reasoning: the manager's
  ``Settings``-bootstrap path constructs a ``Registry`` very early
  and asks for ``ParamSpecs`` before the first tool dispatch, and
  protocol instances don't have ``bind_tool_modules`` results yet
  in some downstream test fixtures. The lazy rebuild keeps the
  observable behavior identical (``list_tools`` etc. always
  return the current inventory) without forcing the index up
  before it's needed.
- **``_normalize_result`` was renamed to ``normalize_result`` when
  it moved into ``dispatcher.py``.** Plan §8.4 keeps the underscore
  spelling on the plugin; phase 5 dropped it because the helper is
  now a public module-level function used by both
  ``SimpleProtocolPlugin`` and ``Registry.run_command``. Underscore
  spelling on a non-class module-level helper would mislead
  importers.

### Test coverage added

``src/tests/framework/test_simple_protocol_phase5.py`` (59 cases):

- **Package layout**: import paths still resolve, internal split is
  reachable, ``SimpleProtocolPlugin`` is still a ``BaseProtocol``
  subclass (3 cases).
- **``decode_payload``**: empty / whitespace-only / flat /
  envelope / envelope-with-non-string-name / envelope-without-
  parameters / envelope-with-non-dict-parameters / invalid-JSON /
  non-object-JSON / string-JSON (10 cases).
- **``convert_type``**: int, float, bool truthy/falsy strings,
  bool pass-through, bool unknown-string fallback, str default,
  unknown-type fallback, ``custom`` pass-through, invalid-int
  graceful-return (10 cases).
- **``find_tool``**: empty modules, qualified resolution to
  specific module, bare-name first match, unknown qualified name,
  module-introspection failure tolerated, tool-def without callable
  rejected (6 cases).
- **``prepare_command_kwargs``**: explicit-precedence, extras
  fallback, positional ``__args__``, default values, required-arg
  raise, type coercion applied, optional-without-value omitted (7
  cases).
- **``normalize_result``**: ``Result`` passthrough, ``str`` wrap,
  invalid-type fail (3 cases).
- **``SimpleProtocolPlugin`` integration**: bind/refbind, read-only
  view of ``bound_modules``, full execute path through payload +
  dispatcher, missing-required-arg propagated (5 cases).
- **``Manager`` binding**: ``iter_protocol_instances`` is public,
  ``_bind_native_tools_to_protocols`` hands modules over, broken
  binder doesn't poison other protocols (3 cases).
- **``Registry`` index + ``execute_tool``**: list aggregation, get
  unknown returns ``None``, first-in-list-wins on duplicate names,
  routing to owning protocol with ``**kwargs`` passthrough,
  unknown-name failure, protocol-exception translation,
  ``refresh_tools`` invalidation rebuilds with new inventory,
  ``refresh_tools`` no-op before load (8 cases).
- **``Registry.run_command``**: dispatcher kwarg-prep reached with
  injectables (registry / settings / conversation), unknown tool
  fails (2 cases).
- **Cleanup verification**: registry no longer carries
  ``_prepare_command_kwargs``, ``_convert_type``, or
  ``_commands_catalog`` (2 cases).

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
- ~~**`SimpleProtocolPlugin.bind_tool_modules` needs a caller.**~~
  Resolved in phase 5: ``Manager._bind_native_tools_to_protocols``
  now calls ``bind_tool_modules`` on every protocol that exposes
  the duck-typed hook, after both ``claia.tool_modules`` and
  ``claia.tool_protocols`` are loaded.
- **`ToolReference.parameter_schema` default.** Made optional
  (``None``) so phase 4 could ship references without forcing a
  schema. Revisit in phase 8 once MCP references need to carry raw
  JSON Schema — the default may need to flip back to required to
  catch protocols that forget to populate it.
- ~~**Registry commands-catalog invalidation.**~~ Resolved in phase
  5: ``_commands_catalog`` was retired; ``refresh_tools`` now
  invalidates the unified ``_tool_index`` /
  ``_protocols_by_name`` view instead.
- **CLI ``parameters`` dicts mix invocation args with Python
  injectables.** ``cli/commands/system.py:HelpCommand`` (and
  similar) shove ``registry``, ``command_specs``, ``current_mode``
  inside ``parameters`` rather than as ``**kwargs`` injectables.
  This is why ``Registry.run_command`` cannot delegate to
  ``execute_tool`` (which JSON-encodes parameters). A follow-up
  should split those callers so ``run_command`` can eventually
  fold into ``execute_tool``.
- **``run_command`` retained for the CLI direct-execution path.**
  Plan §7.4 lets ``run_command`` either forward to ``execute_tool``
  or stay on the registry; phase 5 picked the latter to avoid
  breaking the non-JSON CLI parameter shape (see above). If/when
  the CLI callers split injectables out, revisit removing
  ``run_command`` and folding all CLI dispatch into
  ``execute_tool``.

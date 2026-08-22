# Architectures

The inference layer: an architecture owns the protocol for a model
family — input formatting, talking to the served model, parsing
output, and the family's feature surface. Each class declares the
deployment that serves it via the `deployment` class attribute
(`"api"`, `"transformers"`, ...); the solver follows that link.

## Subpackages

- `api/` — hosted LLM API architectures plus the shared wire utility.
- `base/` — shared base classes and interfaces.
- `dummy/` — test/dummy architectures.
- `transformers/` — local weight-holding architectures.

Generation knobs (`temperature`, `max_tokens`, ...) and credentials
(API tokens, endpoints) are declared together on the **architecture
class** as `@architecture` / `@architecture.param` decorations. Those
become the class-level `ArchitectureInfo.params` list. The
`Registry`/`Manager` resolve RUNTIME kwargs against that list
(filtering + coercion + defaults) and hand the resulting dict to
`generate`, which consumes it directly via `kwargs.get(...)`; INIT
kwargs feed the constructor at deploy time.

`claia.core.plugins.base` exports a shared `COMMON_TEXT_RUNTIME_PARAMS`
list that most text architectures spread into their params; per-
architecture overrides (e.g. Gemma3's higher `max_tokens` default) are
expressed by declaring the override spec on a subclass. Modifier
decorators copy the inherited `info` and prepend the overrides
(first-match-wins by name).

## Contract

`generate(inputs, **kwargs)` — a `MessageSequence` or artifact list
in, `BaseChunk` items yielded up, `ModelResponse` as the generator's
return value. Raise when the request cannot start; once content has
streamed, finish with `response.error` set and `complete=False`.
Errors are never chunk content.

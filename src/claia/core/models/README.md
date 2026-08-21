# Model Layer

Model architecture layer and adapters.

## Subpackages

- `api/` — hosted LLM API clients/adapters.
- `base/` — shared base classes and interfaces.
- `dummy/` — test/dummy models.
- `transformers/` — local transformer-based models.

Generation knobs (`temperature`, `max_tokens`, ...) and credentials
(API tokens, endpoints) are declared together on the **model class**
as `@architecture` / `@architecture.param` decorations. Those become
the class-level `ArchitectureInfo.params` list. The `Registry`/`Manager`
resolve RUNTIME kwargs against that list (filtering + coercion +
defaults) and hand the resulting dict to `BaseModel.generate`, which
consumes it directly via `kwargs.get(...)`.

`claia.core.plugins.base` exports a shared `COMMON_TEXT_RUNTIME_PARAMS`
list that most text architectures spread into their params; per-
architecture overrides (e.g. Gemma3's higher `max_tokens` default) are
expressed by declaring the override spec on a subclass. Modifier
decorators copy the inherited `info` and prepend the overrides
(first-match-wins by name).

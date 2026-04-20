# Model Layer

Model architecture layer and adapters.

## Subpackages

- `api/` — hosted LLM API clients/adapters.
- `base/` — shared base classes and interfaces.
- `dummy/` — test/dummy models.
- `transformers/` — local transformer-based models.

Model implementations expose their generation knobs as RUNTIME `ParamSpec`
declarations via `BaseModel.runtime_params`. Architectures declare their
INIT-scoped `ParamSpec`s (API tokens, endpoints) via `ArchitectureInfo.params`
so the `Registry`/`Manager` can filter kwargs and avoid leaking unrelated
configuration into plugins.

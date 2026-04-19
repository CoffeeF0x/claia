# Model Layer

Model architecture layer and adapters.

## Subpackages

- `api/` — hosted LLM API clients/adapters.
- `base/` — shared base classes and interfaces.
- `dummy/` — test/dummy models.
- `transformers/` — local transformer-based models.

Model implementations typically expose `required_args` so the `Registry`/`Manager` can filter
kwargs and avoid leaking unrelated configuration into plugins.

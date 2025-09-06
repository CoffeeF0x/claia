# CLI

Command-line interface and runtime configuration.

- `__main__.py` — entrypoint for `python -m claia` / `claia`
- `settings.py` — load/validate runtime settings (supports user kwargs)
- `defaults.py` — default prompt/settings presets
- `logger.py` — CLI logging setup

Pass custom settings via CLI; they propagate to agents and models as filtered kwargs.

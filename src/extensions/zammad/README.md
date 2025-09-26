# Zammad Extensions

This extension cleanly separates Zammad integration into:

- `api.py` — `ZammadAPI` for HTTP calls only (returns raw data)
- `utils.py` — `ZammadUtils` for formatting and AI-assisted processes
- `plugin_basic.py` — Basic commands (list, details, tag add/remove, find/delete)
- `plugin_processes.py` — Process commands (AI tagging, untag, account processing, bulk ops)
- `constants.py` — Queries, limits, and prompt templates used by the processors

## Prompts

The following prompt templates are defined in `constants.py` and used by `ZammadUtils`:

- `TAG_PROMPT` — Used in `ZammadUtils.tag_ticket()`
- `ACCOUNT_MANAGEMENT_PROMPT` — Used in `ZammadUtils.process_account_ticket()`
- `VERIFICATION_PROMPT` — Used to verify no data loss when updating account lists
- `SUMMARIZE_PROMPT` — Available for future summarization flows

## Entry points

`pyproject.toml` registers two command modules:

- `extensions.zammad.plugin_basic:ZammadBasicModulePlugin` → module name `zammad`
- `extensions.zammad.plugin_processes:ZammadProcessesModulePlugin` → module name `zammad_processes`

This replaces the old `claia.tools.zammad` module.

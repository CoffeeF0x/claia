# Simple Protocol

Bridges native [`BaseToolModule`](../../../modules/base.py) plugins
into the post-overhaul [`BaseProtocol`](../base.py) contract. This is
the in-tree default for every tool the CLAIA codebase ships; external
authors can write their own modules and they automatically light up
through this protocol.

## Files

| File              | Responsibility                                                           |
| ----------------- | ------------------------------------------------------------------------ |
| `protocol.py`     | `SimpleProtocolPlugin` — `BaseProtocol` impl, lifecycle, inventory.      |
| `dispatcher.py`   | `find_tool`, `prepare_command_kwargs`, `convert_type`, `normalize_result`. |
| `payload.py`      | `decode_payload(raw_payload) -> (parameters, name_hint)`.                |
| `__init__.py`     | Re-exports `SimpleProtocolPlugin` so the `claia.tool_protocols` entry point still resolves at the package path. |

## How dispatch flows

1. The framework loads `SimpleProtocolPlugin` via the
   `simple = "claia.core.tools.protocols.simple:SimpleProtocolPlugin"`
   entry point.
2. After every `claia.tool_modules` plugin is instantiated, the
   `Manager` calls `bind_tool_modules(modules)` so the protocol owns
   a list of native modules to dispatch against.
3. The `Registry` rebuilds its unified tool index by asking every
   loaded protocol — including this one — for its
   `get_tool_references()`. Each native tool surfaces as
   `ToolReference(qualified_name="<module>.<tool>", protocol_name="simple", ...)`.
4. When the agent / CLI calls
   `Registry.execute_tool(qualified_name, raw_payload, conversation, **kwargs)`,
   the registry routes to this protocol's `execute`, which:
   - Decodes `raw_payload` via `payload.decode_payload`.
   - Resolves the callable via `dispatcher.find_tool`.
   - Prepares kwargs (type coercion + injectables) via
     `dispatcher.prepare_command_kwargs`.
   - Invokes the callable and normalizes the return value via
     `dispatcher.normalize_result`.

## Payload shapes

`payload.decode_payload` accepts two JSON shapes:

```jsonc
// Flat — parameters at the top of the object
{"path": "/tmp/foo", "recursive": true}
```

```jsonc
// Envelope — parameters nested under "parameters"
{"name": "fs.read", "parameters": {"path": "/tmp/foo"}}
```

The envelope's `name` field is informational only; dispatch always
uses the `qualified_name` argument supplied by the registry.

## Legacy dispatch

`SimpleProtocolPlugin.execute_legacy(tool_name, parameters, conversation, commands, **kwargs)`
preserves the pre-overhaul calling convention. It is kept alive so
`Registry.process_content`'s transitional shim continues to work
through phase 5; phase 6 retires both together and the method comes
out at the same time.

## CLI direct execution

`Registry.run_command(name, parameters, conversation, **kwargs)` does
**not** go through `execute` — it lives on the registry side because
CLI parameter dicts contain non-JSON-serializable Python objects
(`registry`, `command_specs`, etc.) that must reach the callable
without round-tripping through JSON. That path uses the same
`dispatcher` helpers (`prepare_command_kwargs`, `normalize_result`),
so type coercion stays consistent across the two entry points.

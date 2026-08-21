"""
Tool subsystem for claia.core.

Two plugin types compose the post-overhaul tool system:

- ``modules``: provide groups of executable commands (the actual tools).
- ``protocols``: own a tool inventory and dispatch calls to it. The
  built-in ``simple`` protocol bridges native ``BaseToolModule``
  plugins; future protocols (MCP, etc.) plug in alongside.

ABCs for each live alongside their concrete implementations under this
package. Streaming tool-call extraction lives in ``claia.core.parser``;
the agent loop drives the parser and routes TOOL-tag events through
``Registry.execute_tool``.
"""

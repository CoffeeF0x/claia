"""
Tool subsystem for claia.core.

Three plugin types compose the tool system:

- ``patterns``: detect tool-call invocations inside message content.
- ``protocols``: dispatch a detected call to an executable command.
- ``modules``: provide groups of executable commands (the actual tools).

ABCs for each live alongside their concrete implementations under this
package; the framework exposes mirrored hookspecs in
``claia.framework.hooks``.
"""

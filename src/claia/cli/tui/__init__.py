"""
Textual TUI shell for the CLAIA CLI.

Import ``ClaiaApp`` lazily from the TTY launch path only — this
package (and Textual) must never load for one-shot commands.
"""

from .app import ClaiaApp

__all__ = ["ClaiaApp"]

"""
Strategy 2: throttled full-document re-render via rich Markdown.

  python scripts/md_render_lab/demo_2_rich_rerender.py
"""

# External dependencies
import time

from textual.widgets import Static

# Lab
from harness import LabApp, rich_markdown


########################################################################
#                                 APP                                  #
########################################################################
class RichRerenderLab(LabApp):
  """Keep the full text; restamp one Static about every 50ms."""

  STRATEGY = "rich-rerender"
  RENDER_TICK = 0.05

  async def setup_run(self, body) -> None:
    self._text = ""
    self._widget = Static()
    await body.mount(self._widget)
    self._last_render = 0.0

  async def on_fragment(self, fragment: str) -> None:
    self._text += fragment
    now = time.monotonic()
    if now - self._last_render >= self.RENDER_TICK:
      self._widget.update(rich_markdown(self._text))
      self._last_render = now

  async def on_stream_end(self) -> None:
    self._widget.update(rich_markdown(self._text))


if __name__ == "__main__":
  RichRerenderLab().run()

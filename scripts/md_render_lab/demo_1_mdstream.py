"""
Strategy 1: Textual ``MarkdownStream`` (the baseline).

  python scripts/md_render_lab/demo_1_mdstream.py
"""

# External dependencies
import time

from textual.widgets import Markdown

# Lab
from harness import LabApp


########################################################################
#                                 APP                                  #
########################################################################
class MdStreamLab(LabApp):
  """Feed fragments into ``Markdown.get_stream``."""

  STRATEGY = "mdstream"
  WRITE_TICK = 0.05

  async def setup_run(self, body) -> None:
    self._md = Markdown()
    await body.mount(self._md)
    self._stream = Markdown.get_stream(self._md)
    self._pending = ""
    self._last_write = 0.0

  async def on_fragment(self, fragment: str) -> None:
    self._pending += fragment
    now = time.monotonic()
    if now - self._last_write >= self.WRITE_TICK:
      await self._flush()

  async def on_stream_end(self) -> None:
    await self._flush()

  async def on_stream_close(self) -> None:
    stream = getattr(self, "_stream", None)
    self._stream = None
    if stream is None:
      return
    try:
      await self._flush_into(stream)
    except RuntimeError:
      pass
    await stream.stop()

  async def _flush(self) -> None:
    await self._flush_into(self._stream)

  async def _flush_into(self, stream) -> None:
    if not self._pending or stream is None:
      return
    await stream.write(self._pending)
    self._pending = ""
    self._last_write = time.monotonic()


if __name__ == "__main__":
  MdStreamLab().run()

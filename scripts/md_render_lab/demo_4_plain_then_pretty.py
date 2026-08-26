"""
Strategy 4: plain dim stream, one pretty swap at the end.

  python scripts/md_render_lab/demo_4_plain_then_pretty.py
"""

# External dependencies
from textual.widgets import Static

# Lab
from harness import LabApp, dim_text, rich_markdown


########################################################################
#                                 APP                                  #
########################################################################
class PlainThenPrettyLab(LabApp):
  """Append-only dim text during the stream; render once at end."""

  STRATEGY = "plain-then-pretty"

  async def setup_run(self, body) -> None:
    self._text = ""
    self._widget = Static(dim_text(""))
    await body.mount(self._widget)

  async def on_fragment(self, fragment: str) -> None:
    self._text += fragment
    self._widget.update(dim_text(self._text))

  async def on_stream_end(self) -> None:
    self._widget.update(rich_markdown(self._text))


if __name__ == "__main__":
  PlainThenPrettyLab().run()

"""
Strategy 3: incremental frozen blocks + a plain live tail.

  python scripts/md_render_lab/demo_3_frozen_blocks.py
"""

# External dependencies
from textual.widgets import Static

# Lab
from harness import LabApp, dim_text, rich_markdown, split_frozen_live


########################################################################
#                                 APP                                  #
########################################################################
class FrozenBlocksLab(LabApp):
  """Freeze completed blocks; stream the open tail as dim text."""

  STRATEGY = "frozen-blocks"

  async def setup_run(self, body) -> None:
    self._body = body
    self._acc = ""
    self._frozen_n = 0
    self._tail_text = ""
    self._tail = Static(dim_text(""), classes="tail")
    await body.mount(self._tail)

  async def on_fragment(self, fragment: str) -> None:
    self._acc += fragment
    frozen, live = split_frozen_live(self._acc)
    new_blocks = frozen[self._frozen_n:]
    if new_blocks:
      for source in new_blocks:
        pretty = Static(rich_markdown(source), classes="frozen")
        await self._body.mount(pretty, before=self._tail)
      self._frozen_n = len(frozen)
    if live != self._tail_text:
      self._tail.update(dim_text(live))
      self._tail_text = live

  async def on_stream_end(self) -> None:
    if not self._tail_text:
      return
    pretty = Static(
      rich_markdown(self._tail_text), classes="frozen"
    )
    await self._body.mount(pretty, before=self._tail)
    await self._tail.remove()
    self._tail = None
    self._tail_text = ""


if __name__ == "__main__":
  FrozenBlocksLab().run()

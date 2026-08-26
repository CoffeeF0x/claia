# Markdown render lab

Disposable side-by-side demos for judging how CLAIA should stream
markdown in the Textual TUI. Not part of the package.

Same document, same delivery profiles, same pacer, same bindings
in every demo. The only difference is how arriving fragments are
drawn. Run them from the **repo root** in a real terminal.

```
python scripts/md_render_lab/demo_1_mdstream.py
python scripts/md_render_lab/demo_2_rich_rerender.py
python scripts/md_render_lab/demo_3_frozen_blocks.py
python scripts/md_render_lab/demo_4_plain_then_pretty.py
```

## Bindings

| Key | Action |
|-----|--------|
| `b` | Toggle bursty / steady delivery (restarts) |
| `p` | Toggle pacing on / off (restarts) |
| `r` | Restart the stream |
| `q` | Quit |

Pacing defaults **on**. That is the real design: a shared async
pacer drips characters at ~80/sec and speeds up with backlog so
it never falls far behind. `p` turns it off so you can see raw
wire delivery (bursty stalls and dumps, or a steady 25ms drip).

Status line (identical format in every demo):

```
<strategy> | <profile> | pace on/off | sent/total chars | elapsed | done
```

## Delivery

- **bursty** — token-sized fragments in short bursts, jittered
  stalls, occasional ~0.7s hiccup. Mimics a provider over a
  network.
- **steady** — one small fragment every 25ms.

## Strategies

### 1. `mdstream` — Textual `MarkdownStream`

`Markdown()` + `Markdown.get_stream` + `await stream.write`.
Writes are coalesced to one per ~50ms so the widget is not
pushed past ~20 updates/sec (it degrades above that). This is
the baseline already judged clunky when unpaced; the shared
pacer is the fair re-test.

What to watch for:

- Do completed blocks above the tail visibly re-render or
  flicker as new fragments arrive?
- Does an *open* code fence thrash (re-parse, jump, restyle)
  until the closing backticks land?
- How does a half-built table look mid-stream vs after it
  closes?
- Paced vs unpaced: does the pacer hide clunkiness, or is the
  widget still busy on every write?

### 2. `rich-rerender` — naive throttled re-render

The full accumulated text is restamped onto one `Static` as
`rich.markdown.Markdown` about every 50ms. Simple, O(N²), and
rich paints fences/tables differently from Textual's widget.

What to watch for:

- The whole document re-lays out on every tick — flicker,
  scroll jump, cursor-in-the-tail instability.
- Code fences and tables will *not* match demo 1. That
  difference is the point.
- Incomplete inline markup (`**bo`, `` `co ``) flashes as the
  parser changes its mind.
- Hitching as the document grows; worse unpaced (bigger jumps
  between the same 50ms throttle).

### 3. `frozen-blocks` — custom-engine prototype

markdown-it-py tokenizes the accumulated source. Every
top-level block except the last is frozen: mounted once as
pretty rich Markdown and never touched again. The live tail
streams as append-only dim plaintext. When a new block starts,
the old tail is promoted in place (plain → pretty) and a fresh
dim tail begins. An open ` ``` ` fence is one fence token to
EOF, so the whole fence stays live until it closes.

What to watch for:

- Do completed blocks stay still after they crystallize, or
  does anything above the tail still move?
- The open fence should be calm dim text — no syntax highlight
  until promotion. Confirm it does not flicker.
- Height change at promotion: does the viewport jump when a
  list, fence, or table crystallizes?
- A list or table is one top-level block, so it stays plain
  until the *next* heading/paragraph starts (or the stream
  ends).

### 4. `plain-then-pretty` — smoothness ceiling

The entire message streams as dim plaintext (append-only). At
end of stream the one widget is swapped for a single pretty
rich Markdown render. Zero markdown work while tokens arrive.

What to watch for:

- This is the smoothness ceiling. If another strategy feels
  worse than this while streaming, the cost is the renderer.
- The end-of-stream swap will jump (plain height ≠ pretty
  height). How violent is it?
- Unpaced bursty: even plain text will dump in clumps. That is
  delivery, not rendering.
- Paced: should feel like calm typing the whole way.

## Note

Throw this folder away when the comparison is done. Nothing
here is wired into `claia`.

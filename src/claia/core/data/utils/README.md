# Data Utilities

Small helpers for working with artifact content. These functions are intentionally stateless so they can be reused by the CLI, framework, or external integrations.

## What Lives Here

- `text.py` — base64 encoding, encoding detection/conversion, line ending normalization, truncation, word/line counts, and previews.
- `image.py` — image base64 conversion, dimension/format inspection, metadata extraction, format conversion, resizing, and thumbnails.

## How It Fits

Keep helpers here when they operate on raw content and do not need model, registry, storage, or CLI state. If a helper needs runtime settings or plugin discovery, it belongs in the calling layer instead.

Streaming tool-call extraction lives in `claia.core.parser`, not here — see [`claia/core/parser/README.md`](../../parser/README.md) for the post-overhaul `TagParser` surface.

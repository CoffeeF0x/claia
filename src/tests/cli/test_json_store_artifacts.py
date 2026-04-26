"""
Tests for CLI artifact persistence.
"""

import base64

from claia.cli.storage import JsonStore
from claia.core.data.models import ImageArtifact


PNG_BYTES = base64.b64decode(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_json_store_round_trips_image_artifact_content(tmp_path):
  store = JsonStore(str(tmp_path))
  artifact = ImageArtifact.from_bytes(
    image_data=PNG_BYTES,
    name="generated-image.png",
    format="PNG",
    media_type="image/png",
    metadata={"prompt": "fox"},
  )

  assert store.save(artifact)

  loaded = store.load(artifact.id)

  assert isinstance(loaded, ImageArtifact)
  assert loaded.id == artifact.id
  assert loaded.name == "generated-image.png"
  assert loaded.media_type == "image/png"
  assert loaded.metadata["prompt"] == "fox"
  assert loaded.load_bytes() == PNG_BYTES

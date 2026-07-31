"""
Tests for file import/export CLI commands.
"""

import base64
from types import SimpleNamespace

from claia.cli.commands.core import Commands
from claia.cli.commands.file import ExportFileCommand, FileCommand, ImportFileCommand
from claia.cli.storage import JsonStore
from claia.core.data.models import ImageArtifact


PNG_BYTES = base64.b64decode(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_export_file_command_writes_image_content(tmp_path):
  store = JsonStore(str(tmp_path))
  artifact = ImageArtifact.from_bytes(PNG_BYTES, name="generated.png")
  assert store.save(artifact)

  command = ExportFileCommand(object(), SimpleNamespace(files_directory=str(tmp_path)))
  destination = tmp_path / "exported.png"

  result = command.execute([artifact.id, str(destination)])

  assert result.is_success()
  assert destination.read_bytes() == PNG_BYTES


def test_import_file_command_creates_image_artifact(tmp_path):
  source = tmp_path / "external.png"
  source.write_bytes(PNG_BYTES)

  command = ImportFileCommand(object(), SimpleNamespace(files_directory=str(tmp_path)))

  result = command.execute([str(source), "--name", "imported.png"])

  assert result.is_success()
  artifacts = JsonStore(str(tmp_path)).list_all(artifact_type="images")
  assert len(artifacts) == 1
  loaded = JsonStore(str(tmp_path)).load(artifacts[0]["id"])
  assert isinstance(loaded, ImageArtifact)
  assert loaded.name == "imported.png"
  assert loaded.load_bytes() == PNG_BYTES


def test_file_command_lists_artifacts(tmp_path):
  store = JsonStore(str(tmp_path))
  artifact = ImageArtifact.from_bytes(PNG_BYTES, name="generated.png")
  assert store.save(artifact)

  command = FileCommand(object(), SimpleNamespace(files_directory=str(tmp_path)))

  result = command.execute(["list", "images"])

  assert result.is_success()
  assert artifact.id in result.get_data()
  assert "generated.png" in result.get_data()


def test_cli_command_split_keeps_file_options_with_import_command():
  commands = Commands(object(), SimpleNamespace())

  groups = commands._split_cli_commands(["--import", "external.png", "--name", "imported.png"])

  assert groups == [["--import", "external.png", "--name", "imported.png"]]

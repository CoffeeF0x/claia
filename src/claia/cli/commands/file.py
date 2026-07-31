"""
File import/export commands for persisted CLAIA artifacts.
"""

import mimetypes
import os
from typing import Any, List, Optional

from claia.cli.storage import JsonStore
from claia.core.data.models import AudioArtifact, BaseArtifact, ImageArtifact, TextArtifact
from claia.core.results import Result
from .base import BaseCommand


TEXT_MEDIA_TYPES = {
  "application/json",
  "application/xml",
  "application/javascript",
  "application/x-python-code",
}

ARTIFACT_TYPE_ALIASES = {
  "text": "texts",
  "texts": "texts",
  "image": "images",
  "images": "images",
  "audio": "audio",
  "conversation": "conversations",
  "conversations": "conversations",
  "prompt": "prompts",
  "prompts": "prompts",
}


class FileCommand(BaseCommand):
  """Command to import/export files as stored artifacts."""

  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    if not args:
      return self._show_usage()

    subcommand = args[0].lower()
    if subcommand == "import":
      return self._import_file(args[1:])
    if subcommand == "export":
      return self._export_file(args[1:])
    if subcommand == "list":
      return self._list_files(args[1:])

    return Result(
      success=False,
      message=f"Unknown file subcommand: {subcommand}\nUse {self.format_command('file')} to see available subcommands.",
    )

  def _show_usage(self) -> Result:
    prefix = self.get_help_prefix()
    lines = [
      "\nUsage:",
      f"  {prefix}file list [type]                         - List stored artifacts",
      f"  {prefix}file export <artifact_id> [path]         - Export an artifact to a file",
      f"  {prefix}file import <path> [--name name]         - Import a file as an artifact",
      "",
      "Shortcuts:",
      f"  {prefix}export <artifact_id> [path]",
      f"  {prefix}import <path> [--type image|text|audio]",
    ]
    return Result(success=True, data="\n".join(lines))

  def _import_file(self, args: List[str]) -> Result:
    args = list(args)
    explicit_type = self._consume_option(args, ["--type"])
    name = self._consume_option(args, ["--name"])
    media_type = self._consume_option(args, ["--media-type"])

    if not args:
      return Result(success=False, message=f"Missing source path. Usage: {self.format_command('file import <path>')}")
    if len(args) > 1:
      return Result(success=False, message=f"Unexpected arguments: {' '.join(args[1:])}")

    source = os.path.expanduser(args[0])
    if not os.path.isfile(source):
      return Result(success=False, message=f"File not found: {source}")

    artifact_name = name or os.path.basename(source)
    detected_media_type = media_type or mimetypes.guess_type(artifact_name)[0] or mimetypes.guess_type(source)[0]
    detected_media_type = detected_media_type or "application/octet-stream"
    try:
      kind = self._detect_artifact_kind(artifact_name, detected_media_type, explicit_type)
    except ValueError as e:
      return Result(success=False, message=str(e))
    if not kind:
      return Result(
        success=False,
        message=(
          f"Unsupported file type for import: {detected_media_type}\n"
          "Use --type image, --type text, or --type audio if this file should be handled as one of those artifact types."
        ),
      )

    try:
      with open(source, "rb") as f:
        content = f.read()

      if kind == "image":
        artifact = ImageArtifact.from_bytes(content, name=artifact_name)
      elif kind == "audio":
        artifact = AudioArtifact.from_bytes(content, name=artifact_name)
      else:
        encoding = "utf-8"
        text = content.decode(encoding)
        artifact = TextArtifact.from_content(text, name=artifact_name, encoding=encoding)

      artifact.metadata["source_path"] = os.path.abspath(source)
      store = JsonStore(self.settings.files_directory)
      if not store.save(artifact):
        return Result(success=False, message=f"Failed to import file: {source}")

      return Result(
        success=True,
        data=(
          f"Imported {source}\n"
          f"  ID: {artifact.id}\n"
          f"  Name: {artifact.name}\n"
          f"  Media type: {artifact.media_type}"
        ),
      )
    except UnicodeDecodeError:
      return Result(success=False, message=f"Could not decode text file as UTF-8: {source}")
    except Exception as e:
      self.logger.error(f"Error importing file: {e}", exc_info=True)
      return Result(success=False, message=f"Error importing file '{source}': {str(e)}")

  def _export_file(self, args: List[str]) -> Result:
    args = list(args)
    force = self._consume_flag(args, ["--force"])

    if not args:
      return Result(success=False, message=f"Missing artifact ID. Usage: {self.format_command('file export <artifact_id> [path]')}")
    if len(args) > 2:
      return Result(success=False, message=f"Unexpected arguments: {' '.join(args[2:])}")

    artifact_id = args[0]
    store = JsonStore(self.settings.files_directory)
    artifact = store.load(artifact_id)
    if not artifact:
      return Result(success=False, message=f"Artifact not found: {artifact_id}")

    try:
      content = self._export_content(artifact)
      if content is None:
        return Result(success=False, message=f"Artifact has no embedded exportable content: {artifact_id}")

      destination = args[1] if len(args) == 2 else artifact.name
      destination = os.path.expanduser(destination)
      if os.path.isdir(destination):
        destination = os.path.join(destination, artifact.name)

      parent = os.path.dirname(os.path.abspath(destination))
      if parent and not os.path.isdir(parent):
        return Result(success=False, message=f"Destination directory does not exist: {parent}")
      if os.path.exists(destination) and not force:
        return Result(success=False, message=f"Destination already exists: {destination}\nUse --force to overwrite it.")

      if isinstance(content, str):
        with open(destination, "w", encoding=artifact.metadata.get("encoding", "utf-8")) as f:
          f.write(content)
      else:
        with open(destination, "wb") as f:
          f.write(content)

      return Result(success=True, data=f"Exported {artifact.id} to {destination}")
    except Exception as e:
      self.logger.error(f"Error exporting artifact: {e}", exc_info=True)
      return Result(success=False, message=f"Error exporting artifact '{artifact_id}': {str(e)}")

  def _list_files(self, args: List[str]) -> Result:
    artifact_type = None
    if args:
      artifact_type = ARTIFACT_TYPE_ALIASES.get(args[0].lower())
      if not artifact_type:
        return Result(success=False, message=f"Unknown artifact type: {args[0]}")

    store = JsonStore(self.settings.files_directory)
    rows = store.list_all(artifact_type=artifact_type)
    if not rows:
      return Result(success=True, data="No stored artifacts found.")

    lines = ["Stored artifacts:"]
    for row in rows:
      lines.append(
        f"  {row.get('id')}  {row.get('artifact_type', 'texts')}  "
        f"{row.get('name', 'untitled')}  {row.get('media_type', 'unknown')}  {row.get('size', 0)} bytes"
      )
    return Result(success=True, data="\n".join(lines))

  def _detect_artifact_kind(self, name: str, media_type: str, explicit_type: Optional[str]) -> Optional[str]:
    if explicit_type:
      normalized = explicit_type.lower()
      if normalized in {"image", "text", "audio"}:
        return normalized
      raise ValueError(f"Unsupported import type: {explicit_type}")

    if media_type.startswith("image/"):
      return "image"
    if media_type.startswith("audio/"):
      return "audio"
    if media_type.startswith("text/") or media_type in TEXT_MEDIA_TYPES:
      return "text"
    if name.lower().endswith((".md", ".json", ".yaml", ".yml", ".toml", ".csv")):
      return "text"
    return None

  def _export_content(self, artifact: BaseArtifact):
    if isinstance(artifact, ImageArtifact):
      return artifact.load_bytes()
    if isinstance(artifact, AudioArtifact):
      content = artifact.load_content()
      return content if content else None
    if isinstance(artifact, TextArtifact):
      content = artifact.load_content()
      return content if content else None
    return None

  def _consume_option(self, args: List[str], names: List[str]) -> Optional[str]:
    for name in names:
      if name in args:
        index = args.index(name)
        if index + 1 >= len(args):
          raise ValueError(f"Missing value for {name}")
        value = args[index + 1]
        del args[index:index + 2]
        return value
    return None

  def _consume_flag(self, args: List[str], names: List[str]) -> bool:
    for name in names:
      if name in args:
        args.remove(name)
        return True
    return False


class ImportFileCommand(FileCommand):
  """Shortcut command for importing a file artifact."""

  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    return self._import_file(args)


class ExportFileCommand(FileCommand):
  """Shortcut command for exporting a file artifact."""

  def execute(self, args: List[str], conversation: Optional[Any] = None) -> Result:
    return self._export_file(args)

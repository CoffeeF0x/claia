"""IANA ``application/*`` subtype tokens used by CLAIA."""

from enum import Enum


class ApplicationFormat(Enum):
  """Curated ``application`` subtypes. Grow as needed.

  Enum member names are short; ``.value`` is the IANA subtype token.
  """

  OCTET_STREAM = "octet-stream"
  PDF = "pdf"
  JSON = "json"
  XML = "xml"
  ZIP = "zip"
  DOCX = "vnd.openxmlformats-officedocument.wordprocessingml.document"
  XLSX = "vnd.openxmlformats-officedocument.spreadsheetml.sheet"

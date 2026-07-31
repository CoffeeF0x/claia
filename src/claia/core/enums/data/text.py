"""IANA ``text/*`` subtype tokens used by CLAIA."""

from enum import Enum


class TextFormat(Enum):
  """Curated ``text`` subtypes. Grow as needed."""

  PLAIN = "plain"
  MARKDOWN = "markdown"
  HTML = "html"
  CSV = "csv"
  CSS = "css"
  JAVASCRIPT = "javascript"
  XML = "xml"
  URI_LIST = "uri-list"

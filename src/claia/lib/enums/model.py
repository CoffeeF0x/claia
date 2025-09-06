# External dependencies
from enum import Enum



########################################################################
#                                ENUMS                                 #
########################################################################
class ModelCapability(Enum):
  """Capabilities of a model."""
  DEFAULT = "default"  # Default/fallback capability
  TTT = "text-to-text"
  TTI = "text-to-image"
  ITT = "image-to-text"
  TTS = "text-to-speech"
  STT = "speech-to-text"
  TTA = "text-to-audio"
  TAA = "text-and-audio"
  TAI = "text-and-image"


class IOType(Enum):
  """Input/output types of a model."""
  TEXT = ["txt"]
  IMAGE = ["png", "jpg"]
  AUDIO = ["mp3", "wav"]

class SourcePreference(Enum):
  """Enum for source preferences when deploying models."""
  ANY = "any"  # Use any available source
  API = "api"  # Prefer API sources
  LOCAL = "local"  # Prefer local deployment
  REMOTE = "remote"  # Prefer remote deployment

"""
Architecture implementations for CLAIA's serving stack.

An architecture owns the inference protocol for a model family and
declares which deployment serves it:
- base: Base architecture classes
- api: Hosted-API architectures (served by the ``api`` deployment)
- transformers: In-process architectures (served by ``transformers``)
- dummy: Dummy architecture for testing
"""

# Re-export base classes for convenience. Concrete architectures are
# imported from their own modules (entry points do this) so importing
# this package does not pull heavyweight runtimes like torch.
from .base import BaseArchitecture, APIArchitecture, LocalArchitecture

__all__ = [
  'BaseArchitecture', 'APIArchitecture', 'LocalArchitecture',
]

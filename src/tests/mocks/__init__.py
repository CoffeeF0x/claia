"""Shared test structures and mocks.

Every structure, fixture builder, fake, and mock used by the pytest suite lives in
this package. No test module defines its own structures or mocks outside this
folder — sharing one set of structures keeps every test speaking the same
language.

Layout mirrors the concepts being mocked, e.g.:

  mocks/definitions.py   -> ModelDefinition builders
  mocks/architectures.py -> fake architecture plugins
  mocks/deployments.py   -> fake deployment plugins
  mocks/conversations.py -> Conversation/Message builders

Populated module-by-module as tests migrate to the mirrored structure described
in the ExoFox docs repo at claia/design-philosophy.md.
"""

from enum import Enum


class DeploymentPreference(Enum):
  """Solve-time filter for where a model may run.

  ``LOCAL_ONLY`` — local nodes and non-api deployments only;
  request data never leaves the machine.
  ``REMOTE`` — self-hosted compute only (remote nodes allowed,
  api deployments still excluded).
  ``ANY`` — unrestricted.
  """
  LOCAL_ONLY = "local-only"
  REMOTE = "remote"
  ANY = "any"

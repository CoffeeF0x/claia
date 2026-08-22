"""
Local node.

The in-process host: deployments run on the machine CLAIA itself runs
on, so ``BaseNode``'s default reuse/provision behavior is the whole
job — there is no connection to manage.
"""

from .base import BaseNode
from ..decorators import node


@node
@node.name("local")
@node.title("Local Node")
@node.description("Hosts deployments in-process on the machine CLAIA runs on")
class LocalNode(BaseNode):
  """In-process host for deployments."""

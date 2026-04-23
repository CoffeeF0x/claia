"""
Pluggy registrar wrappers.

Plugin classes in ``claia.core`` are pure implementations of the
``Base*`` ABCs — they depend only on ``claia.core`` and know nothing
about pluggy. The framework is what turns them into pluggy plugins:
for each plugin namespace there is a small registrar class that takes a
plain plugin instance and exposes ``@hookimpl``-decorated methods that
delegate to the wrapped instance.

Keeping pluggy confined to this module lets ``claia.core`` stay
dependency-light (no pluggy in its public contract) while preserving
pluggy-based discovery and hook dispatch in the framework layer.
"""

from __future__ import annotations

import logging
import pluggy
from typing import Any, Dict, Iterator, List, Optional, Type

from claia.core.data import Conversation
from claia.core.modality import GenerationChunk
from claia.core.plugins.base import (
  ArchitectureInfo,
  DeploymentInfo,
  PatternInfo,
  ProtocolInfo,
  SolverInfo,
  ToolCallMatch,
  ToolDefinition,
  ToolModuleInfo,
)
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.results import Result


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Hookimpl markers (one per pluggy namespace)
# ---------------------------------------------------------------------
_arch_impl = pluggy.HookimplMarker("claia_architectures")
_dep_impl = pluggy.HookimplMarker("claia_deployments")
_sol_impl = pluggy.HookimplMarker("claia_solvers")
_def_impl = pluggy.HookimplMarker("claia_definitions")
_pat_impl = pluggy.HookimplMarker("claia_tool_patterns")
_pro_impl = pluggy.HookimplMarker("claia_tool_protocols")
_mod_impl = pluggy.HookimplMarker("claia_tool_modules")
_agt_impl = pluggy.HookimplMarker("claia_agents")


# ---------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------
class _BaseRegistrar:
  """Common surface for all registrars.

  ``plugin`` exposes the wrapped implementation so callers that need
  methods outside the pluggy hookspec (for example, ``Manager`` code
  reaching for ``get_module_tools`` directly) can reach through to
  the pure plugin instance without caring that a wrapper is in the
  way.
  """

  __slots__ = ("_plugin",)

  def __init__(self, plugin: Any) -> None:
    self._plugin = plugin

  @property
  def plugin(self) -> Any:
    return self._plugin

  def __getattr__(self, name: str) -> Any:
    # Delegate unknown attributes to the wrapped plugin so code that
    # operates on the pure ABC surface keeps working against the
    # registrar-wrapped object.
    return getattr(self._plugin, name)


# ---------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------
class ArchitectureRegistrar(_BaseRegistrar):
  """Adapts a ``BaseArchitecture`` instance to the pluggy architecture hooks."""

  @_arch_impl
  def get_architecture_info(self) -> ArchitectureInfo:
    return self._plugin.get_architecture_info()

  @_arch_impl
  def get_model_class(self) -> Type:
    return self._plugin.get_model_class()


# ---------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------
class DeploymentRegistrar(_BaseRegistrar):
  """Adapts a ``BaseDeployment`` instance to the pluggy deployment hooks."""

  @_dep_impl
  def get_deployment_info(self) -> DeploymentInfo:
    return self._plugin.get_deployment_info()

  @_dep_impl
  def run(
    self,
    model_name: str,
    model_class: Type,
    conversation: Conversation,
    cache: Dict[str, Any],
    **kwargs,
  ) -> Iterator[GenerationChunk]:
    return self._plugin.run(
      model_name=model_name,
      model_class=model_class,
      conversation=conversation,
      cache=cache,
      **kwargs,
    )


# ---------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------
class SolverRegistrar(_BaseRegistrar):
  """Adapts a ``BaseSolver`` instance to the pluggy solver hooks."""

  @_sol_impl
  def get_solver_info(self) -> SolverInfo:
    return self._plugin.get_solver_info()

  @_sol_impl
  def can_solve(
    self,
    model_name: str,
    deployment_preference: Optional[str] = None,
    **kwargs,
  ) -> bool:
    return self._plugin.can_solve(
      model_name=model_name,
      deployment_preference=deployment_preference,
      **kwargs,
    )

  @_sol_impl
  def solve_deployment(
    self,
    model_name: str,
    available_deployments: List[str],
    available_models: Dict[str, Any],
    cache: Dict[str, Any],
    deployment_preference: Optional[str] = None,
    deployment_method: Optional[str] = None,
    **kwargs,
  ) -> Result:
    return self._plugin.solve_deployment(
      model_name=model_name,
      available_deployments=available_deployments,
      available_models=available_models,
      cache=cache,
      deployment_preference=deployment_preference,
      deployment_method=deployment_method,
      **kwargs,
    )


# ---------------------------------------------------------------------
# Definition
# ---------------------------------------------------------------------
class DefinitionRegistrar(_BaseRegistrar):
  """Adapts a ``BaseDefinitionProvider`` instance to the pluggy definition hooks."""

  @_def_impl
  def get_definitions(self) -> Dict[str, ModelDefinition]:
    return self._plugin.get_definitions()


# ---------------------------------------------------------------------
# Tool Pattern
# ---------------------------------------------------------------------
class PatternRegistrar(_BaseRegistrar):
  """Adapts a ``BasePattern`` instance to the pluggy tool-pattern hooks."""

  @_pat_impl
  def get_pattern_info(self) -> PatternInfo:
    return self._plugin.get_pattern_info()

  @_pat_impl
  def find_tool_calls(self, content: str, conversation, settings=None) -> List[ToolCallMatch]:
    return self._plugin.find_tool_calls(content, conversation, settings=settings)


# ---------------------------------------------------------------------
# Tool Protocol
# ---------------------------------------------------------------------
class ProtocolRegistrar(_BaseRegistrar):
  """Adapts a ``BaseProtocol`` instance to the pluggy tool-protocol hooks."""

  @_pro_impl
  def get_protocol_info(self) -> ProtocolInfo:
    return self._plugin.get_protocol_info()

  @_pro_impl
  def execute(
    self,
    tool_name: str,
    parameters: Dict[str, Any],
    conversation,
    commands: Dict[str, Any],
    **kwargs,
  ) -> Result:
    return self._plugin.execute(
      tool_name=tool_name,
      parameters=parameters,
      conversation=conversation,
      commands=commands,
      **kwargs,
    )


# ---------------------------------------------------------------------
# Tool Module
# ---------------------------------------------------------------------
class ToolModuleRegistrar(_BaseRegistrar):
  """Adapts a ``BaseToolModule`` instance to the pluggy tool-module hooks."""

  @_mod_impl
  def get_module_info(self) -> ToolModuleInfo:
    return self._plugin.get_module_info()

  @_mod_impl
  def get_module_tools(self) -> Dict[str, ToolDefinition]:
    return self._plugin.get_module_tools()


# ---------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------
class AgentRegistrar(_BaseRegistrar):
  """Adapts an agent plugin to the pluggy agent hooks.

  Agents aren't backed by an ABC in ``claia.core`` (the ``BaseAgent``
  ABC lives in ``claia.framework.agents.base``). The registrar simply
  delegates the two hook methods to the plain plugin, which is expected
  to expose them.
  """

  @_agt_impl
  def get_agent_class(self, agent_name: str):
    return self._plugin.get_agent_class(agent_name)

  @_agt_impl
  def get_agent_info(self):
    return self._plugin.get_agent_info()


# ---------------------------------------------------------------------
# Mapping used by Manager
# ---------------------------------------------------------------------
REGISTRAR_BY_GROUP: Dict[str, Type[_BaseRegistrar]] = {
  "claia.architectures": ArchitectureRegistrar,
  "claia.deployments": DeploymentRegistrar,
  "claia.solvers": SolverRegistrar,
  "claia.definitions": DefinitionRegistrar,
  "claia.tool_patterns": PatternRegistrar,
  "claia.tool_protocols": ProtocolRegistrar,
  "claia.tool_modules": ToolModuleRegistrar,
  "claia.agents": AgentRegistrar,
}


__all__ = [
  "ArchitectureRegistrar",
  "DeploymentRegistrar",
  "SolverRegistrar",
  "DefinitionRegistrar",
  "PatternRegistrar",
  "ProtocolRegistrar",
  "ToolModuleRegistrar",
  "AgentRegistrar",
  "REGISTRAR_BY_GROUP",
]

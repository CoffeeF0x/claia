"""
CLAIA's central registry. A single facade over the module manager
that provides a unified interface for tools, models, and agents.
"""

import logging
import threading
import json
from typing import Any, Dict, Iterator, List, Optional, Union

from claia.framework.manager import Manager
from claia.core.results import Result, DeploymentError
from claia.framework.process import Process
from claia.framework.queue import ProcessQueue
from claia.core.enums.process import ProcessStatus
from claia.core.data import Conversation
from claia.core.modality import ChunkKind, GenerationChunk
from claia.core.plugins.base import ParamScope, ParamSpec



########################################################################
#                              INITIALIZE                              #
########################################################################
logger = logging.getLogger(__name__)



########################################################################
#                               REGISTRY                               #
########################################################################
class Registry:
  """
  Unified registry coordinating tools, models, and agents.

  - Tools API: command catalog, tool-call processing, command execution.
  - Models API: run() orchestration (Solver -> Deployment -> Architecture).
  - Agents API: process queue + worker lifecycle and agent dispatch.
  """

  def __init__(self, process_queue: Optional[ProcessQueue] = None):
    # Core manager and caches
    self._manager = Manager()
    self.cache: Dict[str, Any] = {}

    # Tool-related
    self._commands_catalog: Optional[Dict[str, Dict]] = None
    self._user_kwargs: Dict[str, Any] = {}
    self._plugins_loaded = False

    # Injectables visible to tool callables. Hosts (the CLI, an HTTP
    # service, ...) populate this via ``set_tool_context`` so any tool
    # that declares a matching ``ArgumentDefinition`` (e.g. ``settings``
    # or ``command_specs``) receives the value automatically — no need
    # to forward them through ``run_command`` params. ``registry`` is
    # always injected from ``self`` in ``run_command``.
    self._tool_context: Dict[str, Any] = {}

    # Agent-related (queue and workers)
    self.process_queue = process_queue or ProcessQueue()
    self._workers = []
    self._shutdown = threading.Event()

    # Discover plugins (metadata only) but don't load them yet. This
    # lets ``get_extension_params()`` work before settings are loaded,
    # breaking the circular dependency between extensions and settings.
    self._manager.discover_plugins()

    logger.info("Registry initialized")

  @property
  def manager(self) -> Manager:
    """
    The underlying ``Manager`` instance.

    Exposed as a read-only property so downstream layers (Settings,
    CLI commands, service endpoints) can reach the manager's
    parameter-introspection and coercion helpers without the Registry
    having to re-export each one.
    """
    return self._manager

  def load_plugins(self, **kwargs) -> None:
    """
    Load all plugins with the provided kwargs.

    Each plugin receives only the kwargs matching its ``INIT``-scoped
    ``ParamSpec`` declarations. Call after settings are available.

    Args:
        **kwargs: User settings/configuration to pass to plugins.
    """
    if self._plugins_loaded:
      logger.debug("Plugins already loaded")
      return

    self._user_kwargs.update(kwargs)
    self.manager.load_all_plugins(**self._user_kwargs)
    self._plugins_loaded = True
    logger.debug("Plugins loaded with user kwargs")

  def get_extension_params(self, scope: Optional[ParamScope] = None) -> List[ParamSpec]:
    """
    Return the flat list of ``ParamSpec`` declarations from all
    extensions (deduplicated by ``name``, first declaration wins).

    Settings/CLI layers use this to build flags, env lookups, and
    help text dynamically. Filter by ``scope`` to get only
    ``INIT`` or ``RUNTIME`` specs.
    """
    return self.manager.get_extension_params(scope=scope)

  def update_user_kwargs(self, new_kwargs: Dict[str, Any]) -> None:
    """
    Update the stored user kwargs with new values.
    
    This allows runtime updates to settings that are used by plugins and commands.
    
    Args:
        new_kwargs: Dictionary of new kwargs to merge with existing kwargs
    """
    self._user_kwargs.update(new_kwargs)
    logger.debug(f"Updated user kwargs with {len(new_kwargs)} new values")

  def set_tool_context(self, **context: Any) -> None:
    """Register host-supplied injectables visible to tool callables.

    A tool declares the names it expects as ``ArgumentDefinition``
    entries on its ``ToolDefinition``. When the user invokes the tool
    (e.g. via ``:tool cli.help``) the registry auto-fills those
    arguments from ``tool_context`` so the tool works the same whether
    it's called through a CLI command wrapper or directly.

    Typical CLI wiring::

        registry.set_tool_context(
          settings=settings,
          command_specs=COMMAND_SPECS,
        )

    Per-invocation overrides (via ``run_command`` ``parameters`` or
    ``kwargs``) still win over ``tool_context``.
    """
    self._tool_context.update(context)
    logger.debug(f"Tool context updated with keys: {sorted(context.keys())}")


  ######################################################################
  #                             TOOLS API                              #
  ######################################################################
  def _ensure_loaded(self) -> None:
    """Ensure plugins are loaded and commands catalog is built."""
    if not self._plugins_loaded:
      self.load_plugins()
    if self._commands_catalog is None:
      self._commands_catalog = self.manager.get_all_commands()

  def get_commands_catalog(self) -> Dict[str, Dict]:
    """Return a cached catalog of all commands grouped by module."""
    self._ensure_loaded()
    return self._commands_catalog or {}

  def refresh_tools(self) -> None:
    """Re-fetch dynamic tool inventories from every loaded protocol.

    Phase 4 surface (plan §6.2 / §11 Phase 4). Triggers each
    protocol's :meth:`BaseProtocol.refresh` hook (MCP will react to
    ``notifications/tools/list_changed`` here once it lands). The
    cached command catalog is invalidated so the next call to
    :meth:`get_commands_catalog` rebuilds it; phase 5 will replace that
    with the unified ``_tool_index`` rebuild described in plan §7.1.
    """
    if not self._plugins_loaded:
      return
    self.manager.refresh_protocols()
    self._commands_catalog = None

  def shutdown(self) -> None:
    """Tear down workers and release protocol-owned resources.

    Calls :meth:`stop_workers` and then asks the manager to dispatch
    ``stop()`` across every loaded protocol. Idempotent; safe to call
    even if plugins were never loaded.
    """
    try:
      self.stop_workers(wait=True, timeout=5.0)
    except Exception as e:
      logger.warning("stop_workers raised during shutdown: %s", e)
    if self._plugins_loaded:
      try:
        self.manager.stop_protocols()
      except Exception as e:
        logger.warning("manager.stop_protocols raised during shutdown: %s", e)

  def contains_tool_tokens(self, content: str, pattern_name: Optional[str] = None) -> bool:
    """Lightweight precheck to see if content likely contains tool calls for a pattern."""
    self._ensure_loaded()
    pattern_plugin = None
    pattern_info = None
    if pattern_name:
      pattern_plugin, pattern_info = self.manager.get_pattern_by_name(pattern_name)
    if not pattern_plugin:
      pattern_plugin = self.manager.get_default_pattern()
      if pattern_plugin:
        pattern_info = pattern_plugin.get_pattern_info()
    if not pattern_plugin or not pattern_info:
      return False
    opening_token = getattr(pattern_info, 'opening_token', None)
    if not opening_token:
      return False
    return opening_token in content

  def process_content(self, conversation, content: str, settings=None, protocol_name: str = 'simple', **kwargs) -> str:
    """
    Find and execute tool calls in content using the configured pattern/protocol.
    """
    self._ensure_loaded()

    # Resolve pattern plugin: prefer conversation pattern name, fallback to default
    pattern_plugin = None
    pattern_info = None
    try:
      if conversation and getattr(conversation, 'tool_pattern_name', None):
        pattern_plugin, pattern_info = self.manager.get_pattern_by_name(conversation.tool_pattern_name)
    except Exception:
      pattern_plugin, pattern_info = None, None
    if not pattern_plugin:
      pattern_plugin = self.manager.get_default_pattern()
      if pattern_plugin:
        pattern_info = pattern_plugin.get_pattern_info()
    if not pattern_plugin:
      logger.debug("No tool pattern plugins registered; returning content unchanged")
      return content

    # Resolve protocol plugin
    protocol_plugin, protocol_info = self.manager.get_protocol_by_name(protocol_name)
    if not protocol_plugin:
      logger.warning(f"Tool protocol '{protocol_name}' not found; returning content unchanged")
      return content

    # Pass kwargs through to protocol unchanged
    filtered_protocol_kwargs = dict(kwargs)

    processed = content

    # Prepare the commands catalog once for the protocol to use for lookup
    commands_catalog = self.get_commands_catalog()

    # Iterate until no more matches are found
    while True:
      matches = pattern_plugin.find_tool_calls(processed, conversation, settings=settings)
      if not matches:
        break

      # Process matches in order, left-to-right to keep indices consistent
      for m in matches:
        try:
          # Resolve command definition to prepare arguments
          plugin, cmd_def, module_info = self.manager.get_tool_by_name(m.tool_name)
          if not plugin or not cmd_def:
            exec_result = Result.fail(f"Tool not found: {m.tool_name}")
          else:
            # Extra kwargs can include conversation and user/system kwargs; only mapped if expected by args
            extra = dict(filtered_protocol_kwargs)
            extra['conversation'] = conversation
            prepared_kwargs = self._prepare_command_kwargs(m.parameters or {}, cmd_def, extra_kwargs=extra)

            # Phase 4 transitional shim: dispatch via the pre-overhaul
            # entry point on the simple protocol. The new
            # ``BaseProtocol.execute(qualified_name, raw_payload, ...)``
            # contract is driven by the agent loop in phase 6 once the
            # parser surfaces ``TagEvent`` objects directly; until then
            # the registry keeps feeding prepared kwargs through the
            # legacy dispatch path so existing CLI tool calls work
            # unchanged. See ``tools-overhaul-plan.md`` §7.3.
            exec_result: Result = protocol_plugin.execute_legacy(
              m.tool_name,
              prepared_kwargs,
              conversation,
              commands_catalog,
              **filtered_protocol_kwargs
            )
        except Exception as e:
          exec_result = Result.fail(str(e))

        if exec_result.is_success():
          data = exec_result.get_data()
          if isinstance(data, str):
            replacement = data
          elif data is None:
            replacement = ''
          else:
            try:
              replacement = json.dumps(data)
            except Exception:
              replacement = str(data)
        else:
          replacement = f"[TOOL_ERROR] {exec_result.get_message() or 'Unknown tool error'}"

        # Replace text span
        processed = processed[:m.start_index] + replacement + processed[m.end_index:]

      # Continue loop to detect nested or newly introduced calls

    return processed

  def run_command(self, command_name: str, parameters: Dict[str, Any], conversation, **kwargs) -> Result:
    """Execute a command module by name (for CLI use).
    
    Tool callables must return either:
    - A Result object (used as-is)
    - A string (wrapped in Result.ok)
    - Otherwise an error is returned
    """
    self._ensure_loaded()

    plugin, cmd_def, module_info = self.manager.get_tool_by_name(command_name)
    if not plugin or not cmd_def:
      return Result.fail(f"Tool not found: {command_name}")

    try:
      if not (cmd_def and hasattr(cmd_def, 'callable') and callable(cmd_def.callable)):
        return Result.fail(f"Command '{command_name}' is not executable (no callable)")

      # Build the extras dict that ``_prepare_command_kwargs`` merges
      # into the call. Later assignments override earlier ones, so the
      # precedence (lowest -> highest) is:
      #   tool_context (host-registered injectables, e.g. settings)
      #   -> caller kwargs (per-invocation runtime values)
      #   -> registry (always available, can't be shadowed by kwargs)
      #   -> conversation (current conversation object)
      extra: Dict[str, Any] = {}
      extra.update(self._tool_context)
      extra.update(kwargs)
      extra['registry'] = self
      extra['conversation'] = conversation
      call_kwargs = self._prepare_command_kwargs(parameters or {}, cmd_def, extra_kwargs=extra)

      result = cmd_def.callable(**call_kwargs)
      
      # Handle different return types from tool callables
      if isinstance(result, Result):
        # Tool returned a Result object, use it directly
        return result
      elif isinstance(result, str):
        # Tool returned a string, wrap it in Result.ok
        return Result.ok(data=result)
      else:
        # Invalid return type
        return Result.fail(f"Tool '{command_name}' returned invalid type: {type(result).__name__}. Tools must return Result or str.")
    except Exception as e:
      return Result.fail(str(e))

  def _prepare_command_kwargs(self, parameters: Dict[str, Any], cmd_def, extra_kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Map CLI-provided parameters to the callable's expected arguments.

    Supports both key=value style and positional tokens provided under
    the special key '__args__' (a list of raw string tokens).
    """
    args_spec = getattr(cmd_def, 'arguments', None) or {}
    # Preserve insertion order of args_spec (Python 3.7+ dicts are ordered)
    pos_vals = []
    if isinstance(parameters, dict) and '__args__' in parameters and isinstance(parameters['__args__'], list):
      pos_vals = list(parameters['__args__'])

    # Use extra_kwargs directly since modules now store their required settings internally
    filtered_extra = extra_kwargs or {}

    call_kwargs: Dict[str, Any] = {}

    for name, arg_def in args_spec.items():
      provided = None
      # 1) explicit key=value takes precedence
      if name in parameters:
        provided = parameters[name]
      # 2) use value from filtered extra kwargs (e.g., settings, conversation) if available
      elif name in filtered_extra:
        provided = filtered_extra[name]
      # 3) use positional if available
      elif pos_vals:
        provided = pos_vals.pop(0)
      # 4) default value if present and not provided
      elif hasattr(arg_def, 'default_value') and getattr(arg_def, 'default_value') is not None:
        provided = getattr(arg_def, 'default_value')

      # Validate required
      required = getattr(arg_def, 'required', False)
      if provided is None and required:
        raise ValueError(f"Missing required argument: {name}")

      if provided is not None:
        dtype = getattr(arg_def, 'data_type', 'str')
        call_kwargs[name] = self._convert_type(provided, dtype)

    return call_kwargs

  def _convert_type(self, value: Any, data_type: str) -> Any:
    """Convert string value to the requested data type.

    Supports: 'str', 'int', 'float', 'bool', 'custom'. Falls back to str.
    Custom type passes through values without conversion.
    """
    try:
      if data_type == 'custom':
        # Pass through custom types without conversion
        return value
      if data_type == 'int':
        return int(value)
      if data_type == 'float':
        return float(value)
      if data_type == 'bool':
        if isinstance(value, bool):
          return value
        v = str(value).strip().lower()
        if v in ('1', 'true', 't', 'yes', 'y', 'on'):
          return True
        if v in ('0', 'false', 'f', 'no', 'n', 'off'):
          return False
        # Non-standard bool: treat non-empty as True
        return bool(v)
      # default and 'str'
      return str(value)
    except Exception:
      # If conversion fails, return original value
      return value


  ######################################################################
  #                             MODELS API                             #
  ######################################################################
  def _run_stream(
    self,
    model_name: str,
    conversation: Conversation,
    solver: Optional[str] = None,
    deployment_method: Optional[str] = None,
    deployment_preference: Optional[str] = None,
    **kwargs
  ) -> Iterator[GenerationChunk]:
    """
    Internal: resolve solver/deployment and return the deployment's
    ``GenerationChunk`` iterator. Raises DeploymentError on failure.
    """
    logger.debug(f"Running model {model_name}")

    combined_kwargs = {**self._user_kwargs, **kwargs}

    available_models = self.manager.get_supported_models()
    available_deployments = list(self.manager.get_available_deployments().keys())

    selected_solver = self.manager.get_solver_plugin(solver)
    if not selected_solver:
      raise DeploymentError(f"No solver available (requested: {solver})")

    solver_info = selected_solver.get_solver_info()
    solver_kwargs = Manager.filter_init_kwargs(combined_kwargs, getattr(solver_info, 'params', None))

    params_result = selected_solver.solve_deployment(
      model_name=model_name,
      available_deployments=available_deployments,
      available_models=available_models,
      cache=self.cache,
      deployment_preference=deployment_preference,
      deployment_method=deployment_method,
      **solver_kwargs
    )

    if params_result.is_error():
      raise DeploymentError(params_result.get_message())

    deployment_params = params_result.data
    logger.debug(f"Solver result: deployment={deployment_params.deployment_name} model={deployment_params.model_name} arch={deployment_params.architecture_name}")

    model_class = self.manager.get_model_class(deployment_params.architecture_name)
    if not model_class:
      raise DeploymentError(f"No architecture '{deployment_params.architecture_name}' found for model '{deployment_params.model_name}'")

    provider_model_name = deployment_params.model_name
    model_def = available_models.get(deployment_params.model_name)
    if model_def and getattr(model_def, 'identifiers', None):
      arch_key = deployment_params.architecture_name
      if arch_key in model_def.identifiers:
        provider_model_name = model_def.identifiers[arch_key]
        logger.debug(f"Resolved provider model name for arch '{arch_key}': {provider_model_name}")

    selected_deployment = self.manager.get_deployment_plugin(deployment_params.deployment_name)
    if not selected_deployment:
      raise DeploymentError(f"Deployment method '{deployment_params.deployment_name}' not available")

    deployment_info = selected_deployment.get_deployment_info()
    deployment_params_specs = getattr(deployment_info, 'params', None)
    deployment_init_kwargs = Manager.filter_init_kwargs(combined_kwargs, deployment_params_specs)

    available_architectures = self.manager.get_available_architectures()
    architecture_info = available_architectures.get(deployment_params.architecture_name)
    if architecture_info:
      arch_params = getattr(architecture_info, 'params', None)
      arch_init_kwargs = Manager.filter_init_kwargs(combined_kwargs, arch_params)
      # Architecture RUNTIME specs are the contract for per-call generation
      # knobs (temperature, max_tokens, ...); resolve their declared
      # defaults here so ``model.generate`` receives a complete settings
      # dict and never has to re-derive defaults from a local spec copy.
      arch_runtime_kwargs = Manager.resolve_runtime_kwargs(combined_kwargs, arch_params)
    else:
      arch_init_kwargs = {}
      arch_runtime_kwargs = {}

    deployment_runtime_kwargs = Manager.filter_runtime_kwargs(combined_kwargs, deployment_params_specs)

    # Split by spec scope so each layer gets only the kwargs it
    # consumes: INIT specs feed the model constructor (credentials,
    # endpoints, paths), RUNTIME specs feed ``model.generate``
    # (temperature, max_tokens, ...). Deployment-scoped RUNTIME
    # overrides win over architecture defaults on name collisions.
    init_kwargs = {
      **arch_init_kwargs,
      **deployment_init_kwargs,
    }
    runtime_kwargs = {
      **arch_runtime_kwargs,
      **deployment_runtime_kwargs,
    }

    return selected_deployment.run(
      model_name=provider_model_name,
      model_class=model_class,
      conversation=conversation,
      cache=self.cache,
      init_kwargs=init_kwargs,
      runtime_kwargs=runtime_kwargs,
    )

  def run(
    self,
    model_name: str,
    conversation: Conversation,
    streaming: bool = False,
    **kwargs
  ) -> Union[Result, Iterator[GenerationChunk]]:
    """
    Orchestrate model execution via solver -> deployment -> architecture.

    Args:
        model_name: Model identifier (e.g. "gpt-4")
        conversation: Conversation to process
        streaming: If True, returns an ``Iterator[GenerationChunk]``
                   yielding typed chunks (TEXT tokens, image bytes,
                   progress updates, ...). If False (default), consumes
                   the chunk stream and returns a ``Result`` with the
                   concatenated text payload.
        **kwargs: Forwarded to solver/deployment/architecture (also
                  accepts solver, deployment_method,
                  deployment_preference)

    Returns:
        ``Result`` (streaming=False) or
        ``Iterator[GenerationChunk]`` (streaming=True). Errors raise
        when streaming; errors are wrapped in ``Result.fail`` when
        not streaming.

    For text-only consumers that want plain strings, prefer
    :meth:`stream_text` or the module-level ``iter_text`` helper.
    """
    if streaming:
      return self._run_stream(model_name, conversation, **kwargs)

    try:
      full_response = ""
      for chunk in self._run_stream(model_name, conversation, **kwargs):
        if chunk.kind is ChunkKind.TEXT and isinstance(chunk.data, str):
          full_response += chunk.data
      return Result.ok(full_response)
    except Exception as e:
      logger.error(f"Error running model {model_name}: {e}")
      return Result.fail(str(e))

  def stream_text(
    self,
    model_name: str,
    conversation: Conversation,
    **kwargs
  ) -> Iterator[str]:
    """
    Convenience: stream only the text payload of a generation.

    Wraps :meth:`run` with ``streaming=True`` and yields the string
    data of each ``ChunkKind.TEXT`` chunk, skipping non-text chunks.
    Errors from the underlying deployment propagate as exceptions.
    """
    for chunk in self._run_stream(model_name, conversation, **kwargs):
      if chunk.kind is ChunkKind.TEXT:
        yield chunk.data if isinstance(chunk.data, str) else str(chunk.data)

  def query(
    self,
    model_name: str,
    message: str,
    on_token: Optional[callable] = None,
    on_complete: Optional[callable] = None,
    on_error: Optional[callable] = None,
    agent_type: str = "simple",
    conversation: Optional[Conversation] = None,
    **kwargs
  ) -> Result:
    """
    High-level convenience method: send a message and get a response.

    Creates a Conversation (or reuses the one provided), submits a
    Process with callbacks, waits for completion, and returns the Result.
    This is the simplest way to use CLAIA as a library.

    Args:
        model_name: Model identifier (e.g. "gpt-4")
        message: The user message to send
        on_token: Optional callback fired for each streamed token
        on_complete: Optional callback fired with the full response on success
        on_error: Optional callback fired with error message on failure
        agent_type: Agent type to use (default "simple")
        conversation: Optional existing Conversation to continue
        **kwargs: Extra parameters forwarded to the agent/model

    Returns:
        Result with the full response in data, or an error.
    """
    from claia.core.enums.conversation import MessageRole

    if conversation is None:
      conversation = Conversation()

    conversation.add_message(MessageRole.USER, message)

    done_event = threading.Event()
    result_holder = [None]

    process = Process(
      agent_type=agent_type,
      conversation=conversation,
      parameters={"model_id": model_name, **kwargs}
    )

    if on_token:
      process.on("token", on_token)

    def _on_complete(full_response):
      result_holder[0] = Result.ok(full_response)
      if on_complete:
        on_complete(full_response)
      done_event.set()

    def _on_error(error_msg):
      result_holder[0] = Result.fail(error_msg)
      if on_error:
        on_error(error_msg)
      done_event.set()

    process.on("complete", _on_complete)
    process.on("error", _on_error)

    self.add_process(process)
    done_event.wait()

    return result_holder[0] or Result.fail("Process did not complete")

  def get_supported_models(self) -> Dict[str, Any]:
    """Get all models supported by registered plugins."""
    return self.manager.get_supported_models()

  def get_available_deployments(self) -> Dict[str, Any]:
    """Get all available deployment methods."""
    return self.manager.get_available_deployments()

  def get_available_solvers(self) -> Dict[str, Any]:
    """Get all available deployment solvers."""
    return self.manager.get_available_solvers()

  def get_loaded_models(self) -> Dict[str, Any]:
    """Get dictionary of currently loaded models."""
    return {key: type(model).__name__ for key, model in self.cache.items()}

  def unload_model(self, model_name: str, deployment_method: str = None) -> Result:
    """Unload a model from cache."""
    try:
      if deployment_method:
        cache_key = f"{model_name}:{deployment_method}"
        if cache_key in self.cache:
          del self.cache[cache_key]
          logger.debug(f"Unloaded model {cache_key}")
      else:
        # Remove all instances of this model
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{model_name}:")]
        for key in keys_to_remove:
          del self.cache[key]
          logger.debug(f"Unloaded model {key}")

      return Result(data="Model unloaded successfully")
    except Exception as e:
      return Result.fail(f"Failed to unload model: {str(e)}")

  def unload_all_models(self) -> Result:
    """Unload all models from cache."""
    try:
      self.cache.clear()
      logger.debug("Unloaded all models")
      return Result(data="All models unloaded successfully")
    except Exception as e:
      return Result.fail(f"Failed to unload all models: {str(e)}")

  def get_cache_stats(self) -> Dict[str, Any]:
    """Get statistics about the model cache."""
    return {
      "total_models": len(self.cache),
      "cached_models": list(self.cache.keys())
    }

  ######################################################################
  #                             AGENTS API                             #
  ######################################################################
  def register(
    self,
    agent_class,
    name: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    params: Optional[List[ParamSpec]] = None,
  ) -> None:
    """
    Register a custom agent class programmatically.

    This allows developers to register agents without creating pluggy
    extensions. The agent class must inherit from ``BaseAgent`` and
    implement the ``process_request`` method.

    Example:
        from claia.framework.agents.base import BaseAgent
        from claia.framework import Registry, ParamSpec, ParamScope

        class MyCustomAgent(BaseAgent):
            '''My custom agent implementation.'''

            @classmethod
            def process_request(cls, process, registry=None, **kwargs):
                process.mark_completed(result="Done!")
                return process

        registry = Registry()
        registry.register(
            MyCustomAgent,
            name="my_agent",
            params=[ParamSpec(name="base_url", scope=ParamScope.INIT)],
        )

        process = Process(agent_type="my_agent", ...)
        registry.process(process)

    Args:
        agent_class: The agent class to register (must inherit from BaseAgent).
        name: The name to register the agent under (defaults to class name).
        title: Human-readable display name (defaults to class name).
        description: Description of the agent (defaults to class docstring).
        params: Optional list of ``ParamSpec`` declarations. Names
          matching an ``INIT``-scoped spec are forwarded to the agent
          during dispatch; ``RUNTIME``-scoped specs are used to filter
          per-call overrides.

    Raises:
        ValueError: If the agent class is invalid.
    """
    self.manager.register_agent(
      agent_class=agent_class,
      name=name,
      title=title,
      description=description,
      params=params,
    )

  def process(self, process: Process) -> Process:
    """
    Dispatch the given process to the appropriate agent implementation.
    """
    try:
      logger.debug(f"Processing {process.id} with agent type '{process.agent_type}'")

      # Get the agent class for this agent type
      agent_class = self.manager.get_agent_class(process.agent_type)

      if not agent_class:
        error_msg = f"No agent found for type '{process.agent_type}'"
        logger.error(error_msg)
        process.mark_failed(error_msg)
        return process

      agent_info = self.get_agent_info_by_name(process.agent_type)

      combined_kwargs = {**self._user_kwargs, **process.parameters}

      # Filter kwargs against the agent's declared ParamSpecs. If the
      # agent has no declared params, forward the entire combined set
      # so legacy agents keep working.
      if agent_info and getattr(agent_info, 'params', None):
        init_kwargs = Manager.filter_init_kwargs(combined_kwargs, agent_info.params)
        runtime_kwargs = Manager.filter_runtime_kwargs(combined_kwargs, agent_info.params)
        filtered_kwargs = {**init_kwargs, **runtime_kwargs}
      else:
        filtered_kwargs = combined_kwargs

      # Process using the agent class, injecting this registry and filtered parameters
      logger.debug(f"Using agent class {agent_class.__name__} for {process.id}")
      result = agent_class.process(process, registry=self, **filtered_kwargs)

      return result

    except Exception as e:
      logger.error(f"Error processing {process.id}: {str(e)}")
      process.mark_failed(f"Registry error: {str(e)}")
      return process

  def get_agent_class(self, agent_name: str):
    """Get the agent class for a specific agent name."""
    return self.manager.get_agent_class(agent_name)

  def get_agent_info_by_name(self, agent_name: str):
    """Get agent info for a specific agent name."""
    return self.manager.get_agent_info_by_name(agent_name)

  def add_process(self, process: Process) -> str:
    """Add a process to the queue for execution."""
    return self.process_queue.put(process)

  def process_next(self, block: bool = False, timeout: Optional[float] = None) -> Optional[Process]:
    """Get and process the next process from the queue."""
    process = self.process_queue.get(block=block, timeout=timeout)
    if process:
      # Skip cancelled processes
      if process.status == ProcessStatus.CANCELLED:
        return None

      # Process using this registry
      processed = self.process(process)
      self.process_queue.update(processed)
      return processed
    return None

  def process_by_id(self, process_id: str) -> Optional[Process]:
    """Process a specific process identified by its ID."""
    process = self.process_queue.get_by_id(process_id)
    if process and process.status == ProcessStatus.PENDING:
      processed = self.process(process)
      self.process_queue.update(processed)
      return processed
    return None

  def _worker_loop(self):
    """Worker thread function that processes items from the queue."""
    while not self._shutdown.is_set():
      try:
        # Get and process a single item
        self.process_next(block=True, timeout=1.0)
      except Exception as e:
        logger.exception(f"Error in worker thread: {e}")
        # Continue processing even if one item fails
        continue

    logger.debug("Worker thread shutting down")

  def start_workers(self, num_workers: int = 1):
    """Start worker threads that process items from the queue."""
    logger.info(f"Starting {num_workers} worker threads")
    self._shutdown.clear()

    for i in range(num_workers):
      worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"Registry-Worker-{i+1}")
      worker.start()
      self._workers.append(worker)

    logger.debug(f"Started {num_workers} workers, total active: {len(self._workers)}")

  def stop_workers(self, wait: bool = True, timeout: float = 5.0):
    """Stop all worker threads."""
    logger.info("Stopping worker threads")
    self._shutdown.set()

    if wait:
      workers = list(self._workers)

      for worker in workers:
        worker.join(timeout=timeout / len(workers) if workers else timeout)

      # Clean up worker list
      self._workers = [w for w in self._workers if w.is_alive()]
      if self._workers:
        logger.warning(f"{len(self._workers)} workers still running after timeout")
      else:
        logger.debug("All workers stopped successfully")

  def worker_thread_stats(self) -> tuple[int, int]:
    """
    In-process worker pool counts: ``(registered_threads, alive_threads)``.

    HTTP layers map this to JSON; Claia stays transport-agnostic.
    """
    workers = list(self._workers)
    registered = len(workers)
    alive = sum(1 for w in workers if w.is_alive())
    return (registered, alive)

  def set_worker_count(self, count: int):
    """
    Set the number of worker threads for the Registry.

    If the Registry already has workers, they will be stopped and
    new workers started with the updated count.
    """
    # Ensure at least one worker
    worker_count = max(1, count)

    # Stop existing workers if any
    self.stop_workers(wait=True, timeout=120.0)

    # Start new workers with updated count
    self.start_workers(worker_count)
    logger.debug(f"Updated Registry to use {worker_count} worker(s)")

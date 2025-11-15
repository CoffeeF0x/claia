"""
Unified Registry for CLAIA models, tools, and agents.

This merges the former AgentRegistry, ToolsRegistry, and ModelRegistry into a
single facade over Manager. It exposes the union of their public APIs.
"""

import logging
import threading
import time
import json
from typing import Any, Dict, Optional

from claia.manager import Manager
from claia.lib.results import Result
from claia.lib.process import Process
from claia.lib.queue import ProcessQueue
from claia.lib.enums.process import ProcessStatus
from claia.lib.data import Conversation



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

  def __init__(self, manager: Optional[Manager] = None, process_queue: Optional[ProcessQueue] = None, **kwargs):
    # Core manager and caches
    self.manager = manager or Manager()
    self.cache: Dict[str, Any] = {}

    # Tool-related
    self._commands_catalog: Optional[Dict[str, Dict]] = None
    self._user_kwargs = kwargs

    # Agent-related (queue and workers)
    self.process_queue = process_queue or ProcessQueue()
    self._workers = []
    self._shutdown = threading.Event()

    # Load plugins up front with user kwargs (for command modules required_args)
    self.manager.load_all_plugins(**self._user_kwargs)
    logger.info("Registry initialized successfully")

  def update_user_kwargs(self, new_kwargs: Dict[str, Any]) -> None:
    """
    Update the stored user kwargs with new values.
    
    This allows runtime updates to settings that are used by plugins and commands.
    
    Args:
        new_kwargs: Dictionary of new kwargs to merge with existing kwargs
    """
    self._user_kwargs.update(new_kwargs)
    logger.debug(f"Updated user kwargs with {len(new_kwargs)} new values")


  ######################################################################
  #                             TOOLS API                              #
  ######################################################################
  def _ensure_loaded(self) -> None:
    """Ensure plugins are loaded and commands catalog is built."""
    self.manager.load_all_plugins(**self._user_kwargs)
    if self._commands_catalog is None:
      self._commands_catalog = self.manager.get_all_commands()

  def get_commands_catalog(self) -> Dict[str, Dict]:
    """Return a cached catalog of all commands grouped by module."""
    self._ensure_loaded()
    return self._commands_catalog or {}

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

            exec_result: Result = protocol_plugin.execute(
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

      # Prepare keyword args for the callable based on its command definition
      extra = dict(kwargs)
      # Allow commands to opt-in to receiving conversation by declaring an argument named 'conversation'
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

    Supports: 'str', 'int', 'float', 'bool'. Falls back to str.
    """
    try:
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
  def run(
    self,
    model_name: str,
    conversation: Conversation,
    solver: Optional[str] = None,
    deployment_method: Optional[str] = None,
    deployment_preference: Optional[str] = None,
    **kwargs
  ) -> Result:
    """
    Orchestrate model execution via solver → deployment → architecture.
    """
    try:
      logger.debug(f"Running model {model_name}")

      # Merge user kwargs from Registry initialization with run-time kwargs
      # Run-time kwargs take precedence over initialization kwargs
      combined_kwargs = {**self._user_kwargs, **kwargs}

      # Get available models and deployments
      available_models = self.manager.get_supported_models()
      available_deployments = list(self.manager.get_available_deployments().keys())

      # Get solver plugin
      selected_solver = self.manager.get_solver_plugin(solver)
      if not selected_solver:
        return Result.fail(f"No solver available (requested: {solver})")

      # Filter kwargs for solver based on required_args
      solver_info = selected_solver.get_solver_info()
      solver_kwargs = self._filter_kwargs(combined_kwargs, getattr(solver_info, 'required_args', None))

      # Call solver to determine deployment
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
        return params_result

      deployment_params = params_result.data
      logger.debug(f"Solver result: deployment={deployment_params.deployment_name} model={deployment_params.model_name} arch={deployment_params.architecture_name}")

      # Resolve model class from architecture plugins using architecture name
      model_class = self.manager.get_model_class(deployment_params.architecture_name)
      if not model_class:
        return Result.fail(f"No architecture '{deployment_params.architecture_name}' found for model '{deployment_params.model_name}'")

      # Resolve provider-specific model identifier for the selected architecture
      provider_model_name = deployment_params.model_name
      model_def = available_models.get(deployment_params.model_name)
      if model_def and getattr(model_def, 'identifiers', None):
        arch_key = deployment_params.architecture_name
        if arch_key in model_def.identifiers:
          provider_model_name = model_def.identifiers[arch_key]
          logger.debug(f"Resolved provider model name for arch '{arch_key}': {provider_model_name}")

      # Get deployment plugin
      selected_deployment = self.manager.get_deployment_plugin(deployment_params.deployment_name)
      if not selected_deployment:
        return Result.fail(f"Deployment method '{deployment_params.deployment_name}' not available")

      # Filter kwargs for deployment based on required_args
      deployment_info = selected_deployment.get_deployment_info()
      deployment_kwargs = self._filter_kwargs(combined_kwargs, getattr(deployment_info, 'required_args', None))

      # Also get architecture kwargs for the model class
      available_architectures = self.manager.get_available_architectures()
      architecture_info = available_architectures.get(deployment_params.architecture_name)
      if architecture_info:
        architecture_kwargs = self._filter_kwargs(combined_kwargs, getattr(architecture_info, 'required_args', None))
        # Merge architecture kwargs with deployment kwargs (deployment takes precedence)
        final_kwargs = {**architecture_kwargs, **deployment_kwargs}
      else:
        final_kwargs = deployment_kwargs

      # Let deployment plugin handle deployment + inference
      result = selected_deployment.run(
        model_name=provider_model_name,
        model_class=model_class,
        conversation=conversation,
        cache=self.cache,
        **final_kwargs
      )

      return result

    except Exception as e:
      logger.error(f"Error running model {model_name}: {str(e)}")
      return Result.fail(f"Failed to run model: {str(e)}")

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

  def _filter_kwargs(self, kwargs: Dict[str, Any], required_args: Optional[list]) -> Dict[str, Any]:
    """Filter kwargs to only include those specified in required_args."""
    if required_args is None or len(required_args) == 0:
      # If no required_args specified, return empty dict
      return {}

    # Filter to only include kwargs that are in the required_args list
    filtered = {}
    for arg_name in required_args:
      if arg_name in kwargs:
        filtered[arg_name] = kwargs[arg_name]

    return filtered


  ######################################################################
  #                             AGENTS API                             #
  ######################################################################
  def register(
    self,
    agent_class,
    name: Optional[str] = None,
    description: Optional[str] = None,
    required_args: Optional[list] = None
  ) -> None:
    """
    Register a custom agent class programmatically.
    
    This allows developers to register agents without creating pluggy extensions.
    The agent class must inherit from BaseAgent and implement the process_request method.
    
    Example:
        from claia.lib import BaseAgent
        from claia import registry
        
        class MyCustomAgent(BaseAgent):
            '''My custom agent implementation.'''
            
            @classmethod
            def process_request(cls, process, registry=None, **kwargs):
                # Your custom logic here
                process.mark_completed(result="Done!")
                return process
        
        # Register the agent
        registry.register(MyCustomAgent, name="my_agent")
        
        # Now you can use it
        process = Process(agent_type="my_agent", ...)
        registry.process(process)
    
    Args:
        agent_class: The agent class to register (must inherit from BaseAgent)
        name: The name to register the agent under (defaults to class name)
        description: Description of the agent (defaults to class docstring)
        required_args: Optional list of required arguments for the agent
    
    Raises:
        ValueError: If the agent class is invalid
    """
    self.manager.register_agent(
      agent_class=agent_class,
      name=name,
      description=description,
      required_args=required_args
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

      # Get agent info to filter kwargs based on required_args
      agent_info = self.get_agent_info_by_name(process.agent_type)

      # Combine process parameters with user kwargs from registry initialization
      combined_kwargs = {**self._user_kwargs, **process.parameters}

      # Filter kwargs based on agent's required_args (only if a non-empty list is provided)
      if agent_info and getattr(agent_info, 'required_args', None):
        filtered_kwargs = self._filter_kwargs(combined_kwargs, agent_info.required_args)
      else:
        # If no agent info or no required_args, pass through all combined kwargs
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

"""
Stepwise agent execution tests.

One worker dispatch runs one agent step; loop state rides
``task.parameters``; the queue re-enqueues tasks whose step reported
``CONTINUE`` until a step is terminal. Covers:

- The queued path end-to-end (``add_task`` → ``dispatch_next``),
  including the regression where dispatch merges ``task.parameters``
  (``model_id``) into the agent kwargs.
- Multi-step tasks re-enqueueing and interleaving fairly.
- Cooperative cancellation between steps.
- The legacy started transition firing exactly once per task.
- ``AgentStatus`` conversion (including a step returning garbage).
- The direct path (``execute``) driving steps to completion.
"""

# External dependencies
import pytest

# Internal dependencies
from claia.core.data import Conversation
from claia.core.enums.agent import AgentStatus
from claia.core.enums.conversation import MessageRole
from claia.core.enums.task import TaskEvent, TaskStatus
from claia.framework.agents.base import BaseAgent
from claia.framework.agents.simple import SimpleAgent
from claia.framework.task import Task


class CountingAgent(BaseAgent):
  """Test agent: continues until ``count`` reaches ``target``."""

  @classmethod
  def step(cls, task, registry, **kwargs) -> AgentStatus:
    count = task.parameters.get("count", 0) + 1
    task.parameters["count"] = count
    if count >= task.parameters.get("target", 3):
      task.result = f"done@{count}"
      return AgentStatus.COMPLETED
    return AgentStatus.CONTINUE


class BadStatusAgent(BaseAgent):
  """Test agent whose step returns a non-AgentStatus value."""

  @classmethod
  def step(cls, task, registry, **kwargs):
    return "definitely not an AgentStatus"


def _task(agent_type="simple", target=None):
  conversation = Conversation(title="t")
  conversation.add_message(MessageRole.USER, "hi")
  parameters = {"model_id": "dummy"}
  if target is not None:
    parameters["target"] = target
  return Task(agent_type=agent_type, conversation=conversation, parameters=parameters)


def _registry_with_agent(registry, agent_class):
  """Shadow agent lookup on the fixture registry instance."""
  registry.get_agent_class = lambda name: agent_class
  registry.get_agent_info_by_name = lambda name: None
  return registry


# ---------------------------------------------------------------------------
# Queued path
# ---------------------------------------------------------------------------
class TestQueuedDispatch:
  def test_simple_agent_completes_off_the_queue(self, registry_with_fake_manager):
    """Regression: dispatch merges task.parameters (model_id) into the
    agent kwargs; the chat step must drop task-owned keys instead of
    forwarding them into the model call."""
    reg = _registry_with_agent(registry_with_fake_manager, SimpleAgent)
    task = _task()

    reg.add_task(task)
    dispatched = reg.dispatch_next()

    assert dispatched is task
    assert task.status == TaskStatus.COMPLETED
    assert task.error is None
    assert "deployed dummy via api" in task.result
    assert task.parameters[BaseAgent.ROUND_PARAMETER] == 1

  def test_multi_step_task_requeues_until_terminal(self, registry_with_fake_manager):
    reg = _registry_with_agent(registry_with_fake_manager, CountingAgent)
    task = _task(agent_type="counting", target=3)
    reg.add_task(task)

    first = reg.dispatch_next()
    assert first is task
    assert task.status == TaskStatus.PENDING
    assert task.parameters["count"] == 1

    second = reg.dispatch_next()
    assert second is task
    assert task.status == TaskStatus.PENDING
    assert task.parameters["count"] == 2

    third = reg.dispatch_next()
    assert third is task
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "done@3"

    # Nothing left in line.
    assert reg.dispatch_next() is None

  def test_two_tasks_interleave_steps(self, registry_with_fake_manager):
    reg = _registry_with_agent(registry_with_fake_manager, CountingAgent)
    task_a = _task(agent_type="counting", target=2)
    task_b = _task(agent_type="counting", target=2)
    reg.add_task(task_a)
    reg.add_task(task_b)

    order = [reg.dispatch_next().id for _ in range(4)]

    assert order == [task_a.id, task_b.id, task_a.id, task_b.id]
    assert task_a.status == TaskStatus.COMPLETED
    assert task_b.status == TaskStatus.COMPLETED

  def test_cancel_between_steps(self, registry_with_fake_manager):
    reg = _registry_with_agent(registry_with_fake_manager, CountingAgent)
    task = _task(agent_type="counting", target=5)
    cancelled = []
    task.on(TaskEvent.CANCELLED, lambda result=None: cancelled.append(result))
    reg.add_task(task)

    reg.dispatch_next()
    assert task.status == TaskStatus.PENDING

    task.request_cancel()
    reg.dispatch_next()

    assert task.status == TaskStatus.CANCELLED
    assert len(cancelled) == 1
    # No further step ran after the cancellation.
    assert task.parameters["count"] == 1

  def test_started_at_stamped_once_across_steps(self, registry_with_fake_manager):
    reg = _registry_with_agent(registry_with_fake_manager, CountingAgent)
    task = _task(agent_type="counting", target=3)
    assert task.started_at is None
    reg.add_task(task)

    first = reg.dispatch_next()
    stamped = first.started_at
    assert stamped is not None

    while reg.dispatch_next() is not None:
      pass

    assert task.status == TaskStatus.COMPLETED
    assert task.started_at == stamped

  def test_terminal_task_popped_from_queue_is_skipped(self, registry_with_fake_manager):
    reg = _registry_with_agent(registry_with_fake_manager, CountingAgent)
    task = _task(agent_type="counting", target=1)
    reg.add_task(task)
    task.mark_completed("already done elsewhere")

    assert reg.dispatch_next() is None
    assert task.parameters.get("count") is None


# ---------------------------------------------------------------------------
# AgentStatus conversion
# ---------------------------------------------------------------------------
class TestAgentStatusConversion:
  def test_step_must_return_agent_status(self, fake_model_registry_ok):
    task = _task()
    BadStatusAgent.run(task, registry=fake_model_registry_ok)
    assert task.status == TaskStatus.FAILED
    assert "must return an AgentStatus" in task.error

  def test_step_not_implemented_fails_task(self, fake_model_registry_ok):
    class NoStepAgent(BaseAgent):
      pass

    task = _task()
    NoStepAgent.run(task, registry=fake_model_registry_ok)
    assert task.status == TaskStatus.FAILED
    assert "must override step" in task.error


# ---------------------------------------------------------------------------
# Direct path
# ---------------------------------------------------------------------------
class TestDirectExecute:
  def test_execute_drives_steps_to_completion(self, fake_model_registry_ok):
    task = _task(agent_type="counting", target=4)
    updated = CountingAgent.execute(task, registry=fake_model_registry_ok)

    assert updated is task
    assert task.status == TaskStatus.COMPLETED
    assert task.result == "done@4"
    assert task.parameters["count"] == 4

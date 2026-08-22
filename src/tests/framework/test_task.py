"""
Unit tests for claia.framework.task.Task
"""

# External dependencies
import time
import re

# Internal dependencies
from claia.framework.task import Task
from claia.core.enums.task import TaskEvent, TaskStatus


def test_task_initialization_defaults(conversation):
  t = Task(conversation=conversation)
  # id should be a UUID-like string
  assert isinstance(t.id, str) and re.match(r"^[0-9a-f\-]{36}$", t.id)
  assert t.agent_type == "simple"
  assert t.status == TaskStatus.PENDING
  assert t.parent_id is None
  assert t.parameters == {}
  assert t.result is None
  assert t.error is None
  assert isinstance(t.created_at, float)
  assert t.started_at is None
  assert t.completed_at is None


def test_mark_started_sets_status_and_started_at(task):
  created_at = task.created_at
  time.sleep(0.01)
  task.mark_started()
  assert task.status == TaskStatus.PROCESSING
  assert task.started_at is not None
  assert task.started_at >= created_at


def test_mark_completed_sets_status_result_and_timestamp(task):
  task.mark_started()
  time.sleep(0.01)
  result_payload = {"ok": True}
  task.mark_completed(result_payload)
  assert task.status == TaskStatus.COMPLETED
  assert task.result == result_payload
  assert task.completed_at is not None
  assert task.completed_at >= task.started_at


def test_mark_failed_sets_status_error_and_timestamp(task):
  task.mark_started()
  time.sleep(0.005)
  task.mark_failed("boom")
  assert task.status == TaskStatus.FAILED
  assert task.error == "boom"
  assert task.completed_at is not None
  assert task.completed_at >= task.started_at


def test_mark_cancelled_sets_status_and_timestamp(task):
  task.mark_cancelled()
  assert task.status == TaskStatus.CANCELLED
  assert task.completed_at is not None


def test_mark_cancelled_emits_cancelled(task):
  seen = []
  task.on(TaskEvent.CANCELLED, lambda result: seen.append(result))
  task.mark_cancelled("partial")
  assert task.result == "partial"
  assert seen == ["partial"]


def test_on_rejects_string_event_name(task):
  try:
    task.on("cancelled", lambda result: None)
  except TypeError as exc:
    assert "TaskEvent" in str(exc)
  else:
    raise AssertionError("expected TypeError")

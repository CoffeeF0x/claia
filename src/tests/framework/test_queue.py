"""
Unit tests for claia.framework.queue.TaskQueue
"""

# External dependencies
import threading
import time

# Internal dependencies
from claia.framework.queue import TaskQueue
from claia.core.enums.task_queue import TaskQueueHook
from claia.framework.task import Task
from claia.core.enums.task import TaskStatus


def test_put_and_get_returns_same_task(task: Task):
  q = TaskQueue()
  tid = q.put(task)
  assert tid == task.id
  assert q.size() == 1

  got = q.get(block=False)
  assert got is task
  assert q.size() == 0


def test_get_empty_returns_none():
  q = TaskQueue()
  got = q.get(block=False)
  assert got is None


def test_get_by_id_returns_task(task: Task):
  q = TaskQueue()
  tid = q.put(task)
  looked_up = q.get_by_id(tid)
  assert looked_up is task


def test_remove_marks_cancelled_and_get_pops(task: Task):
  q = TaskQueue()
  tid = q.put(task)
  assert q.remove(tid) is True

  # On retrieval, cancelled tasks are popped from lookup
  got = q.get(block=False)
  assert got is task
  assert got.status == TaskStatus.CANCELLED
  assert q.get_by_id(tid) is None


def test_update_allows_mutation(task: Task):
  q = TaskQueue()
  tid = q.put(task)

  # mutate task and update
  task.parameters["x"] = 1
  q.update(task)
  assert q.get_by_id(tid).parameters["x"] == 1


def test_wait_for_task_returns_when_completed(task: Task):
  q = TaskQueue()
  tid = q.put(task)

  def worker():
    time.sleep(0.05)
    task.mark_completed({"ok": True})
    q.update(task)

  t = threading.Thread(target=worker)
  t.start()

  done = q.wait_for_task(tid, timeout=1, check_interval=0.01)
  t.join()

  assert done is task
  assert done.status == TaskStatus.COMPLETED
  assert done.result == {"ok": True}


def test_wait_for_task_timeout_returns_pending(task: Task):
  q = TaskQueue()
  tid = q.put(task)
  # Do not complete it; expect the implementation to return the task object
  # (still pending) after timeout
  got = q.wait_for_task(tid, timeout=0.05, check_interval=0.01)
  assert got is task
  assert got.status == TaskStatus.PENDING


def test_wait_for_all_tasks_pending_timeout_false(task: Task):
  q = TaskQueue()
  q.put(task)
  all_done = q.wait_for_all_tasks(timeout=0.05, check_interval=0.01)
  assert all_done is False


def test_queue_native_hooks_enqueue_and_dequeue(task: Task):
  q = TaskQueue()
  seen = []

  def on_enq(**kw):
    seen.append(("enq", kw["task"].id))

  def on_deq(**kw):
    seen.append(("deq", kw["task"].id))

  q.add_hook(TaskQueueHook.ENQUEUE, on_enq)
  q.add_hook(TaskQueueHook.DEQUEUE, on_deq)

  q.put(task)
  got = q.get(block=False)
  assert got is task
  assert seen == [("enq", task.id), ("deq", task.id)]

  q.remove_hook(TaskQueueHook.ENQUEUE, on_enq)
  q.remove_hook(TaskQueueHook.DEQUEUE, on_deq)


def test_queue_snapshot_includes_task_fields(task: Task):
  q = TaskQueue()
  q.put(task)
  snap = q.snapshot()
  assert len(snap) == 1
  row = snap[0]
  assert row["id"] == task.id
  assert row["status"] == "pending"
  assert row["agent_type"] == task.agent_type
  assert "model_id" in row["parameters"]

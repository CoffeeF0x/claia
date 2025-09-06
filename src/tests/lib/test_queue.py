"""
Unit tests for claia.lib.queue.ProcessQueue
"""

# External dependencies
import threading
import time

# Internal dependencies
from claia.lib.queue import ProcessQueue
from claia.lib.process import Process
from claia.lib.enums.process import ProcessStatus


def test_put_and_get_returns_same_process(process: Process):
  q = ProcessQueue()
  pid = q.put(process)
  assert pid == process.id
  assert q.size() == 1

  got = q.get(block=False)
  assert got is process
  assert q.size() == 0


def test_get_empty_returns_none():
  q = ProcessQueue()
  got = q.get(block=False)
  assert got is None


def test_get_by_id_returns_process(process: Process):
  q = ProcessQueue()
  pid = q.put(process)
  looked_up = q.get_by_id(pid)
  assert looked_up is process


def test_remove_marks_cancelled_and_get_pops(process: Process):
  q = ProcessQueue()
  pid = q.put(process)
  assert q.remove(pid) is True

  # On retrieval, cancelled processes are popped from lookup
  got = q.get(block=False)
  assert got is process
  assert got.status == ProcessStatus.CANCELLED
  assert q.get_by_id(pid) is None


def test_update_allows_mutation(process: Process):
  q = ProcessQueue()
  pid = q.put(process)

  # mutate process and update
  process.parameters["x"] = 1
  q.update(process)
  assert q.get_by_id(pid).parameters["x"] == 1


def test_wait_for_process_returns_when_completed(process: Process):
  q = ProcessQueue()
  pid = q.put(process)

  def worker():
    time.sleep(0.05)
    process.mark_completed({"ok": True})
    q.update(process)

  t = threading.Thread(target=worker)
  t.start()

  done = q.wait_for_process(pid, timeout=1, check_interval=0.01)
  t.join()

  assert done is process
  assert done.status == ProcessStatus.COMPLETED
  assert done.result == {"ok": True}


def test_wait_for_process_timeout_returns_pending(process: Process):
  q = ProcessQueue()
  pid = q.put(process)
  # Do not complete it; expect the implementation to return the process object
  # (still pending) after timeout
  got = q.wait_for_process(pid, timeout=0.05, check_interval=0.01)
  assert got is process
  assert got.status == ProcessStatus.PENDING


def test_wait_for_all_processes_pending_timeout_false(process: Process):
  q = ProcessQueue()
  q.put(process)
  all_done = q.wait_for_all_processes(timeout=0.05, check_interval=0.01)
  assert all_done is False


def test_wait_for_all_processes_no_pending_true(process: Process):
  q = ProcessQueue()
  # Once not PENDING, the current implementation treats as all done
  process.mark_started()
  q.put(process)
  all_done = q.wait_for_all_processes(timeout=0.5, check_interval=0.01)
  assert all_done is True

"""
Unit tests for claia.lib.process.Process
"""

# External dependencies
import time
import re

# Internal dependencies
from claia.lib.process import Process
from claia.lib.enums.process import ProcessStatus


def test_process_initialization_defaults(conversation):
  p = Process(conversation=conversation)
  # id should be a UUID-like string
  assert isinstance(p.id, str) and re.match(r"^[0-9a-f\-]{36}$", p.id)
  assert p.agent_type == "simple"
  assert p.status == ProcessStatus.PENDING
  assert p.parent_id is None
  assert p.parameters == {}
  assert p.result is None
  assert p.error is None
  assert isinstance(p.created_at, float)
  assert p.started_at is None
  assert p.completed_at is None


def test_mark_started_sets_status_and_started_at(process):
  created_at = process.created_at
  time.sleep(0.01)
  process.mark_started()
  assert process.status == ProcessStatus.PROCESSING
  assert process.started_at is not None
  assert process.started_at >= created_at


def test_mark_completed_sets_status_result_and_timestamp(process):
  process.mark_started()
  time.sleep(0.01)
  result_payload = {"ok": True}
  process.mark_completed(result_payload)
  assert process.status == ProcessStatus.COMPLETED
  assert process.result == result_payload
  assert process.completed_at is not None
  assert process.completed_at >= process.started_at


def test_mark_failed_sets_status_error_and_timestamp(process):
  process.mark_started()
  time.sleep(0.005)
  process.mark_failed("boom")
  assert process.status == ProcessStatus.FAILED
  assert process.error == "boom"
  assert process.completed_at is not None
  assert process.completed_at >= process.started_at


def test_mark_cancelled_sets_status_and_timestamp(process):
  process.mark_cancelled()
  assert process.status == ProcessStatus.CANCELLED
  assert process.completed_at is not None

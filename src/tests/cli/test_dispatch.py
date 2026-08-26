"""
Dispatch matrix for the one-shot entry point.

Covers the args / TTY / piped-stdin combinations and the exit-code
mapping (failures must exit non-zero).
"""

from claia.cli.__main__ import resolve_invocation, result_exit_code
from claia.core.results import Result



########################################################################
#                          INVOCATION MATRIX                           #
########################################################################
class TestResolveInvocation:
  def test_args_on_a_terminal_run_one_shot(self):
    assert resolve_invocation(["model", "list"], True, None) == (
      "run", ["model", "list"],
    )

  def test_piped_stdin_becomes_implicit_query(self):
    assert resolve_invocation([], False, "hello") == (
      "run", ["--query", "hello"],
    )

  def test_piped_stdin_prepends_to_existing_args(self):
    assert resolve_invocation(["--verbose", "true"], False, "hello") == (
      "run", ["--query", "hello", "--verbose", "true"],
    )

  def test_empty_pipe_with_args_still_runs(self):
    assert resolve_invocation(["help"], False, None) == ("run", ["help"])

  def test_terminal_without_args_shows_help(self):
    assert resolve_invocation([], True, None) == ("help", [])

  def test_empty_pipe_without_args_is_usage_error(self):
    assert resolve_invocation([], False, None) == ("usage", [])



########################################################################
#                              EXIT CODES                              #
########################################################################
class TestResultExitCode:
  def test_success_is_zero(self):
    assert result_exit_code(Result(success=True)) == 0

  def test_failure_is_nonzero(self):
    assert result_exit_code(Result(success=False, message="nope")) == 1

  def test_exit_result_keeps_its_code(self):
    assert result_exit_code(Result(success=True, exit=True, exit_code=3)) == 3

  def test_exit_result_with_zero_code(self):
    assert result_exit_code(Result(success=True, exit=True, exit_code=0)) == 0

  def test_failed_exit_result_is_still_nonzero(self):
    assert result_exit_code(Result(success=False, exit=True, exit_code=0)) == 1

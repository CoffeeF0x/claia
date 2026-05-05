"""Tests for bare-message / implicit --query CLI routing."""

from types import SimpleNamespace

from claia.cli.commands.core import Commands


def test_implicit_query_group_joins_unknown_leading_token():
  commands = Commands(object(), SimpleNamespace())

  assert commands._maybe_implicit_query_group(['hi', 'there']) == ['--query', 'hi', 'there']
  assert commands._maybe_implicit_query_group(["how's", 'the', 'weather?']) == [
    '--query',
    "how's",
    'the',
    'weather?',
  ]


def test_implicit_query_skips_explicit_cli_and_interactive_commands():
  commands = Commands(object(), SimpleNamespace())

  assert commands._maybe_implicit_query_group(['--query', 'hi']) == ['--query', 'hi']
  assert commands._maybe_implicit_query_group(['--help']) == ['--help']
  assert commands._maybe_implicit_query_group(['-h']) == ['-h']
  assert commands._maybe_implicit_query_group(['query', 'hi']) == ['query', 'hi']
  assert commands._maybe_implicit_query_group(['h']) == ['h']


def test_implicit_query_skips_unknown_flags():
  commands = Commands(object(), SimpleNamespace())

  assert commands._maybe_implicit_query_group(['--not-a-real-command']) == ['--not-a-real-command']

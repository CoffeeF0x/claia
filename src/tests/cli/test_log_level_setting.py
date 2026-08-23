"""Live :set log_level / log_format must reconfigure the process logger."""

import logging
import sys

import pytest

from claia.cli.logger import initialize_logging
from claia.cli.settings import Settings


@pytest.fixture
def isolated_logging():
  root = logging.getLogger()
  saved_level = root.level
  saved_handlers = list(root.handlers)
  yield
  root.handlers.clear()
  for handler in saved_handlers:
    root.addHandler(handler)
  root.setLevel(saved_level)


@pytest.fixture
def settings(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  monkeypatch.setattr(sys, "argv", ["claia"])
  monkeypatch.delenv("CLAIA_LOG_LEVEL", raising=False)
  monkeypatch.delenv("LOG_LEVEL", raising=False)
  monkeypatch.delenv("CLAIA_LOG_FORMAT", raising=False)
  monkeypatch.delenv("LOG_FORMAT", raising=False)
  return Settings()


def test_update_log_level_applies_to_session(settings, isolated_logging):
  initialize_logging("warning", "standard")
  root = logging.getLogger()
  assert root.level == logging.WARNING

  success, _, _ = settings.update_setting("log_level", "debug")

  assert success
  assert settings.log_level == "debug"
  assert root.level == logging.DEBUG
  assert root.handlers
  assert all(handler.level == logging.DEBUG for handler in root.handlers)


def test_reset_log_level_reapplies_default(settings, isolated_logging):
  settings.update_setting("log_level", "debug")
  assert logging.getLogger().level == logging.DEBUG

  success, _, _ = settings.reset_setting("log_level")

  assert success
  assert logging.getLogger().level == logging.WARNING

"""
Tests for framework-side plugin decorators and manager discovery.

Covers ``@agent`` inference, the stray-stash warning, and the
manifest-path registration helper including identity dedupe.
"""

import logging
import types

import pytest

from claia.core.decorators import PENDING_ATTR, _decorated_plugins, tool
from claia.core.tools.modules.base import BaseToolModule
from claia.framework.agents.base import BaseAgent
from claia.framework.agents.simple import SimpleAgent
from claia.framework.decorators import agent
from claia.framework.manager import PLUGIN_GROUPS, Manager, PluginEntry


########################################################################
#                              FIXTURES                                #
########################################################################
@pytest.fixture(autouse=True)
def _restore_decorated_plugins():
  """Keep the manifest collection from leaking across tests."""
  snapshot = list(_decorated_plugins)
  try:
    yield
  finally:
    _decorated_plugins[:] = snapshot


########################################################################
#                               AGENT                                  #
########################################################################
def test_agent_decorator_infers_title_and_description_leaves_class_unset():
  @agent(name="probe")
  class ProbeAgent(BaseAgent):
    """A probe agent for decorator tests.

    Second paragraph must not be used.
    """

  assert ProbeAgent.info.name == "probe"
  assert ProbeAgent.info.title == "Probe Agent"
  assert ProbeAgent.info.description == "A probe agent for decorator tests."
  assert ProbeAgent.info.agent_class is None


def test_simple_agent_stacked_decorators_match_catalog():
  assert SimpleAgent.info.name == "simple"
  assert SimpleAgent.info.title == "Simple Agent"
  assert SimpleAgent.info.description == (
    "A simple agent that directly calls a model for inference"
  )


def test_register_plugin_class_fills_agent_class():
  @agent(name="helper_agent")
  class HelperAgent(BaseAgent):
    """Helper agent."""

  manager = Manager()
  manager._lazy_plugins = {group: {} for group in PLUGIN_GROUPS}
  entry = manager._register_plugin_class(
    "claia.agents", "helper_agent", HelperAgent,
  )
  assert entry is not None
  assert entry.info.agent_class is HelperAgent
  assert HelperAgent.info.agent_class is HelperAgent


def test_register_plugin_class_skips_non_agent():
  class NotAnAgent:
    pass

  manager = Manager()
  manager._lazy_plugins = {group: {} for group in PLUGIN_GROUPS}
  entry = manager._register_plugin_class("claia.agents", "nope", NotAnAgent)
  assert entry is None
  assert manager._lazy_plugins["claia.agents"] == {}


########################################################################
#                         STRAY STASH WARNING                          #
########################################################################
def test_stray_stash_warns_when_main_decorator_missing(caplog):
  @tool.name("orphan")
  class OrphanPlugin:
    pass

  assert PENDING_ATTR in OrphanPlugin.__dict__
  assert "info" not in OrphanPlugin.__dict__

  manager = Manager()
  entry = PluginEntry(
    name="orphan",
    group="claia.tool_modules",
    entry_point=None,
    plugin_class=OrphanPlugin,
  )
  with caplog.at_level(logging.WARNING, logger="claia.framework.manager"):
    manager._populate_entry_metadata(entry)

  assert entry.info is None
  assert any(PENDING_ATTR in record.getMessage() for record in caplog.records)


def test_successful_decoration_does_not_leave_a_stash():
  @tool
  @tool.name("clean")
  class CleanPlugin(BaseToolModule):
    """Clean."""

  assert PENDING_ATTR not in CleanPlugin.__dict__
  assert CleanPlugin.info.name == "clean"


########################################################################
#                    MANIFEST PATH / IDENTITY DEDUPE                   #
########################################################################
def test_register_plugin_class_first_in_wins_on_name():
  @tool(name="shared_name")
  class FirstMod(BaseToolModule):
    """First."""

  @tool(name="shared_name")
  class SecondMod(BaseToolModule):
    """Second."""

  manager = Manager()
  manager._lazy_plugins = {group: {} for group in PLUGIN_GROUPS}
  first = manager._register_plugin_class(
    "claia.tool_modules", "shared_name", FirstMod,
  )
  second = manager._register_plugin_class(
    "claia.tool_modules", "shared_name", SecondMod,
  )
  assert first is not None
  assert second is None
  assert (
    manager._lazy_plugins["claia.tool_modules"]["shared_name"].plugin_class
    is FirstMod
  )


def test_register_decorated_plugins_identity_dedupe(caplog):
  @tool(name="already_there")
  class AlreadyThere(BaseToolModule):
    """Already registered via the helper."""

  @tool(name="from_manifest")
  class FromManifest(BaseToolModule):
    """Only in the decorator collection."""

  manager = Manager()
  manager._lazy_plugins = {group: {} for group in PLUGIN_GROUPS}
  registered = manager._register_plugin_class(
    "claia.tool_modules", "already_there", AlreadyThere,
  )
  assert registered is not None

  with caplog.at_level(logging.DEBUG, logger="claia.framework.manager"):
    added, _secrets = manager._register_decorated_plugins()

  assert (
    manager._lazy_plugins["claia.tool_modules"]["already_there"].plugin_class
    is AlreadyThere
  )
  assert (
    manager._lazy_plugins["claia.tool_modules"]["from_manifest"].plugin_class
    is FromManifest
  )
  assert added >= 1
  assert any("identity dedupe" in record.getMessage() for record in caplog.records)


def test_manifest_entry_point_import_registers_new_class(monkeypatch):
  captured = {}

  def _load_manifest():
    @tool(name="fake_manifest_mod")
    class FakeManifestMod(BaseToolModule):
      """Loaded via a fake claia.plugins entry point."""
    captured["cls"] = FakeManifestMod
    return types.ModuleType("fake_manifest_pkg")

  class _ManifestEP:
    name = "fakepkg"
    value = "fake_manifest_pkg"

    def load(self):
      return _load_manifest()

  real_entry_points = __import__("importlib.metadata", fromlist=["entry_points"]).entry_points
  real = real_entry_points()

  class _EntryPoints:
    def select(self, group):
      if group == "claia.plugins":
        return [_ManifestEP()]
      return real.select(group=group)

  monkeypatch.setattr(
    "claia.framework.manager.metadata.entry_points",
    lambda: _EntryPoints(),
  )

  manager = Manager()
  manager.discover_plugins()

  modules = manager._lazy_plugins["claia.tool_modules"]
  assert "fake_manifest_mod" in modules
  assert modules["fake_manifest_mod"].plugin_class is captured["cls"]
  from claia.core.tools.modules.sample import SampleToolModule
  assert "sample" in modules
  assert modules["sample"].plugin_class is SampleToolModule
  agents = manager._lazy_plugins["claia.agents"]
  assert agents["simple"].plugin_class is SimpleAgent


def test_plugin_groups_excludes_manifest_group():
  assert "claia.plugins" not in PLUGIN_GROUPS

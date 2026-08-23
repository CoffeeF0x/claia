"""ToolChunk shape and SolverResult native-tool capability."""

from claia.core.data.chunks import TextChunk, ToolChunk
from claia.core.definitions.model_definition import ModelDefinition
from claia.core.enums.data import ApplicationFormat, MediaType
from claia.core.plugins.base import ServingPlan
from claia.framework.solver import SolverResult


def test_tool_chunk_is_application_json():
  chunk = ToolChunk(
    tool_name="demo.echo",
    payload={"message": "hi"},
    call_id="c1",
  )
  assert chunk.type is MediaType.APPLICATION
  assert chunk.format is ApplicationFormat.JSON
  assert chunk.tool_name == "demo.echo"
  assert chunk.payload == {"message": "hi"}
  assert chunk.call_id == "c1"
  assert chunk.data == {"message": "hi"}
  assert chunk.metadata["tool_name"] == "demo.echo"
  assert chunk.metadata["call_id"] == "c1"


def _result(definition) -> SolverResult:
  return SolverResult(
    plan=ServingPlan(
      model_name="m",
      provider_model_name="m",
      architecture_name="a",
      deployment_name="d",
      node_name="n",
    ),
    definition=definition,
    architecture_class=object,
    deployment=object(),
    node=object(),
  )


def test_supports_native_tools_from_outputs():
  native = _result(ModelDefinition(outputs=[TextChunk, ToolChunk]))
  text_only = _result(ModelDefinition(outputs=[TextChunk]))
  assert native.supports_native_tools is True
  assert text_only.supports_native_tools is False

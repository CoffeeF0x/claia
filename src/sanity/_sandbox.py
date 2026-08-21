from claia.core.definitions.model_definition import ModelDefinition
from claia.core.results import DeploymentError
from claia.framework.registry import Registry


definitions = {
  "gpt-test": ModelDefinition(
    title="GPT Test",
    aliases=["gpt"],
    deployments=["api"],
    architectures=["openai"],
  ),
  "gemma-test": ModelDefinition(
    title="Gemma Test",
    deployments=["local", "api"],
    architectures=["transformers_gemma3"],
  ),
  "broken-test": ModelDefinition(
    title="Broken Test",
    deployments=[],
    architectures=[],
  ),
}

available_deployments = ["api", "local"]

requests = [
  ("gpt-test", None),
  ("gpt", None),
  ("gemma-test", None),
  ("gemma-test", "local"),
  ("gemma-test", "remote"),
  ("broken-test", None),
  ("missing-model", None),
]

for model_name, deployment_method in requests:
  label = f"{model_name} ({deployment_method or 'auto'})"
  try:
    params = Registry._resolve_deployment(
      model_name,
      definitions,
      available_deployments,
      deployment_method=deployment_method,
    )
    print(f"{label:28} -> {params.deployment_name} / {params.architecture_name} / {params.model_name}")
  except DeploymentError as e:
    print(f"{label:28} -> FAIL: {e}")

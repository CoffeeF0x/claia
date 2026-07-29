from claia.core.definitions.model_definition import ModelDefinition
from claia.core.solvers.default import DefaultSolverPlugin

MODULE = DefaultSolverPlugin


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

solver = MODULE()
print(solver.get_solver_info().name, "-", solver.get_solver_info().description)
print()

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
  result = solver.solve_deployment(
    model_name,
    available_deployments,
    definitions,
    {},
    deployment_method=deployment_method,
  )
  label = f"{model_name} ({deployment_method or 'auto'})"
  if result.is_success():
    params = result.get_data()
    print(f"{label:28} -> {params.deployment_name} / {params.architecture_name} / {params.model_name}")
  else:
    print(f"{label:28} -> FAIL: {result.get_message()}")

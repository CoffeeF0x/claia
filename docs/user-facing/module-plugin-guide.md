# CLAIA Plugin System Guide

This guide explains how to create and register external plugins for the CLAIA model system.

## Overview

The CLAIA plugin system uses **pluggy** with **entry points** for extensible plugin discovery. There are three types of plugins:

1. **Model Plugins**: Implement specific AI models (OpenAI, Anthropic, etc.)
2. **Deployment Plugins**: Handle deployment methods (API, local, remote)
3. **Solver Plugins**: Determine deployment strategies based on preferences

## Creating External Plugins

### 1. Model Plugin Example

Create a new package with your model plugin:

```python
# my_model_plugin/plugin.py
import logging
from typing import Dict, List, Type, Optional
from claia.src.models.hooks.model_hooks import ModelInfo
from claia.src.models.base import BaseModel

logger = logging.getLogger(__name__)

class MyCustomModel(BaseModel):
    """Your custom model implementation."""

    def __init__(self, model_name: str, **kwargs):
        super().__init__(model_name, **kwargs)
        # Initialize your model here

    def generate(self, conversation, **kwargs):
        # Implement your model's generation logic
        pass

class MyCustomModelPlugin:
    """Plugin for custom model integration."""

    def get_model_info(self) -> Dict[str, ModelInfo]:
        """Return information about supported models."""
        return {
            "my-custom-model": ModelInfo(
                name="my-custom-model",
                title="My Custom Model",
                description="A custom AI model implementation",
                provider="MyCompany",
                aliases=["custom", "my-model"],
                capabilities=["text-generation"],
                settings={}
            )
        }

    def get_supported_models(self) -> Dict[str, ModelInfo]:
        """Return all models supported by this plugin."""
        return self.get_model_info()

    def get_model_class(self, model_name: str) -> Optional[Type[BaseModel]]:
        """Return the model class for a specific model."""
        if model_name == "my-custom-model":
            return MyCustomModel
        return None

    def supports_specialized_loading(self, model_name: str) -> bool:
        """Whether this plugin handles specialized loading."""
        return False
```

### 2. Deployment Plugin Example

```python
# my_deployment_plugin/plugin.py
import logging
from typing import Dict, Type, Any
from claia.src.models.hooks.deployment_hooks import DeploymentInfo
from claia.src.models.base import BaseModel
from common.results import Result

logger = logging.getLogger(__name__)

class MyCustomDeploymentPlugin:
    """Custom deployment method plugin."""

    def get_deployment_info(self) -> DeploymentInfo:
        """Get information about this deployment method."""
        return DeploymentInfo(
            name="my-custom",
            title="My Custom Deployment",
            description="Custom deployment method with special features",
            supported_model_types=["api", "local"],
            settings={}
        )

    def can_deploy(self, model_name: str, model_type: str, **kwargs) -> bool:
        """Check if this deployment can handle the model."""
        return model_type in ["api", "local"]

    def deploy_model(self, model_name: str, model_class: Type, **kwargs) -> Result:
        """Deploy/initialize a model."""
        try:
            # Your custom deployment logic here
            model_instance = model_class(
                model_name=model_name,
                # Add your custom parameters
                **kwargs
            )

            return Result(data=model_instance)
        except Exception as e:
            return Result.fail(f"Deployment failed: {str(e)}")

    def run_model(self, model_instance: BaseModel, conversation, **kwargs) -> Result:
        """Run inference on the deployed model."""
        try:
            response = model_instance.generate(conversation, **kwargs)
            return Result(data=response)
        except Exception as e:
            return Result.fail(f"Inference failed: {str(e)}")
```

### 3. Solver Plugin Example

```python
# my_solver_plugin/plugin.py
import logging
from typing import Optional, Dict, List, Any
from claia.src.models.hooks.solver_hooks import SolverInfo, DeploymentDecision
from common.results import Result

logger = logging.getLogger(__name__)

class MyCustomSolverPlugin:
    """Custom solver with specialized deployment logic."""

    def get_solver_info(self) -> SolverInfo:
        """Get information about this solver."""
        return SolverInfo(
            name="my-custom-solver",
            title="My Custom Solver",
            description="Solver with custom deployment logic",
            priority=50,  # Higher priority than default (100)
            settings={}
        )

    def can_solve(self, model_name: str, deployment_preference: Optional[str] = None, **kwargs) -> bool:
        """Check if this solver can handle the request."""
        # Example: Only handle GPU-intensive models
        return "large" in model_name or "gpu" in kwargs

    def solve_deployment(
        self,
        model_name: str,
        available_deployments: List[str],
        available_models: Dict[str, Any],
        deployment_preference: Optional[str] = None,
        deployment_method: Optional[str] = None,
        **kwargs
    ) -> Result[DeploymentDecision]:
        """Determine the best deployment method."""
        try:
            # Your custom logic here
            if "gpu" in kwargs and "remote" in available_deployments:
                chosen_deployment = "remote"
            elif "api" in available_deployments:
                chosen_deployment = "api"
            else:
                return Result.fail("No suitable deployment found")

            return Result(data=DeploymentDecision(
                deployment_method=chosen_deployment,
                model_name=model_name,
                model_type="custom",
                deployment_params=kwargs,
                confidence=0.9
            ))

        except Exception as e:
            return Result.fail(f"Solver error: {str(e)}")
```

## Registering Plugins

### Option 1: Entry Points in pyproject.toml

Add your plugins to your package's `pyproject.toml`:

```toml
[project.entry-points."claia.models"]
my-custom = "my_model_plugin.plugin:MyCustomModelPlugin"

[project.entry-points."claia.deployments"]
my-custom = "my_deployment_plugin.plugin:MyCustomDeploymentPlugin"

[project.entry-points."claia.solvers"]
my-custom = "my_solver_plugin.plugin:MyCustomSolverPlugin"
```

### Option 2: Programmatic Registration

For development or testing, you can register plugins programmatically:

```python
from claia.src.models.manager import ModuleManager

# Get the manager instance
manager = ModuleManager()

# Register your plugins directly
manager.model_pm.register(MyCustomModelPlugin())
manager.deployment_pm.register(MyCustomDeploymentPlugin())
manager.solver_pm.register(MyCustomSolverPlugin())
```

## Installation and Usage

1. **Install your plugin package**:
   ```bash
   pip install my-custom-claia-plugin
   ```

2. **The plugin will be automatically discovered** when CLAIA loads

3. **Use your models**:
   ```python
   from claia.src.models.registry import ModelRegistry

   registry = ModelRegistry()
   result = registry.run("my-custom-model", conversation)
   ```

## Plugin Development Tips

1. **Follow the hook interfaces** defined in `src/models/hooks/`
2. **Handle errors gracefully** - return `Result.fail()` for errors
3. **Add proper logging** for debugging
4. **Test your plugins** with the existing system
5. **Use priority values** in solvers to control precedence
6. **Document your plugin's requirements** and configuration

## Discovery Process

The system discovers plugins in this order:

1. **Entry points** from installed packages (preferred)
2. **Built-in plugins** as fallback
3. **Minimal fallback** plugins if all else fails

This ensures the system always has working plugins while allowing full extensibility.

# Current Architecture & Structure

## Folder/Module Structure
- agents
- cli
- commands
- common
- extensions
- models
- tests

## Current Architecture
- models
  - registry
  - definitions: defines information and relations for the model (aliases, deployments, architecture, etc)
  - solvers: select the best deployment method or model based on input parameters
  - deployments: handles the deployment of the model (or passes to cloud for api based deployments)
    - runpod-transformers
  - architectures
    - transformers-default
    - transformers-gemma


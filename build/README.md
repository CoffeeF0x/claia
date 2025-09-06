# Build

Build and deployment support.

- `requirements.txt` — pinned dependencies for build contexts
  - (allows us to avoid rebuilding dev context in dockerfile for every pyproject.toml change)
- `deploy.sh` — deployment helper script

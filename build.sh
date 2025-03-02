#!/bin/bash
BINARY_NAME=${1:-"claia"}
DIST_DIR=${2:-"dist"}

# Install dependencies
pip install -r requirements.txt --no-cache-dir

# Build binary
pyinstaller --onefile \
  --name "${BINARY_NAME}" \
  --add-data "src/models:models" \
  --add-data "src/commands:commands" \
  --add-data "src/modules:modules" \
  --add-data "src/tools:tools" \
  --distpath "${DIST_DIR}" \
  src/main.py

# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${DIST_DIR}/version.txt"
fi
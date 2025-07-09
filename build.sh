#!/bin/bash
BINARY_NAME=${1:-"claia"}
DIST_DIR=${2:-"dist"}

# Install dependencies
pip install -r requirements.txt --no-cache-dir

# Build binary
pyinstaller --onefile \
  --name "${BINARY_NAME}" \
  --add-data "old/src/models:models" \
  --add-data "old/src/commands:commands" \
  --add-data "old/modules:modules" \
  --add-data "old/src/tools:tools" \
  --distpath "${DIST_DIR}" \
  old/src/main.py

# --hidden-import "PyQt6.QtGui" \


# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${DIST_DIR}/version.txt"
fi
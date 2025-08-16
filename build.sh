#!/bin/bash
BINARY_NAME=${1:-"claia"}
DIST_DIR=${2:-"dist"}

# Install dependencies
pip install -r requirements.txt --no-cache-dir

# Build binary
pyinstaller --onefile \
  --name "${BINARY_NAME}" \
  --paths src \
  --distpath "${DIST_DIR}" \
  src/cli/__main__.py

# --hidden-import "PyQt6.QtGui" \


# Copy requirements.txt to distribution
cp requirements.txt "${DIST_DIR}/"

# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${DIST_DIR}/version.txt"
fi
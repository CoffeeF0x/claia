#!/bin/bash
BINARY_NAME=${1:-"claia"}
BUILD_DIR=${2:-"build"}
DIST_DIR=${3:-"dist"}

# Create build directories
mkdir -p "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"

# Install dependencies
pip install -r requirements.txt --no-cache-dir

# Copy source files
cp -r src/* "${BUILD_DIR}/"

# Build binary
cd "${BUILD_DIR}"
pyinstaller --onefile \
  --name "${BINARY_NAME}" \
  --add-data "models:models" \
  --add-data "commands:commands" \
  --add-data "functions:functions" \
  main.py

# Move binary to dist
mv "${BINARY_NAME}" "../${DIST_DIR}/"

# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "../${DIST_DIR}/version.txt"
fi
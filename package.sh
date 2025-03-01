#!/bin/bash
PACKAGE_NAME=${1:-"claia"}
DIST_DIR=${2:-"dist"}
TEMP_DIR=$(mktemp -d)

# Create dist directory if it doesn't exist
mkdir -p "${DIST_DIR}"

# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${DIST_DIR}/version.txt"
fi

# Copy source files to temp directory
cp -r src/* "${TEMP_DIR}/"
cp requirements.txt README.md "${TEMP_DIR}/"

# Package source code
cd "${TEMP_DIR}" && zip -r "${DIST_DIR}/${PACKAGE_NAME}.zip" . -x "**/__pycache__/**" "**/*.pyc"

# Clean up
rm -rf "${TEMP_DIR}"
#!/bin/bash
PACKAGE_NAME=${1:-"claia"}
DIST_DIR=${2:-"dist"}
TEMP_DIR=$(mktemp -d)
WORK_DIR=$(pwd)

# Create dist directory if it doesn't exist
mkdir -p "${WORK_DIR}/${DIST_DIR}"

# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${WORK_DIR}/${DIST_DIR}/version.txt"
fi

# Copy source files to temp directory
cp -r src-old/* "${TEMP_DIR}/"
cp requirements.txt README.md "${TEMP_DIR}/"

# Package source code
cd "${TEMP_DIR}"
zip -r "${WORK_DIR}/${DIST_DIR}/${PACKAGE_NAME}.zip" . -x "**/__pycache__/**" "**/*.pyc"
cd "${WORK_DIR}"

# Clean up
rm -rf "${TEMP_DIR}"
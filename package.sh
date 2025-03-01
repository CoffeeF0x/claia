#!/bin/bash
PACKAGE_NAME=${1:-"claia"}
DIST_DIR=${2:-"dist"}

# Create dist directory if it doesn't exist
mkdir -p "${DIST_DIR}"

# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${DIST_DIR}/version.txt"
fi

# Package source code
zip -r "${DIST_DIR}/${PACKAGE_NAME}.zip" src/ requirements.txt README.md -x "**/__pycache__/**" "**/*.pyc"
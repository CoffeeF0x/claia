#!/bin/bash
MODE=${1:-"package"}  # binary or package
NAME=${2:-"claia"}
DIST_DIR=${3:-"dist"}

# Create dist directory if it doesn't exist
mkdir -p "${DIST_DIR}"

# Create version file
if [ ! -z "$CI_COMMIT_SHA" ]; then
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${DIST_DIR}/version.txt"
fi

if [ "$MODE" = "binary" ]; then
  echo "Building binary executable..."

  # Install dependencies
  pip install -r requirements.txt --no-cache-dir

  # Build wheel distribution
  python -m build --wheel --outdir "${WORK_DIR}/${DIST_DIR}"

  # Build binary
  pyinstaller --onefile \
    --name "${NAME}" \
    --paths src \
    --distpath "${DIST_DIR}" \
    src/cli/__main__.py

  # --hidden-import "PyQt6.QtGui" \

elif [ "$MODE" = "package" ]; then
  echo "Creating package distribution..."

  TEMP_DIR=$(mktemp -d)
  WORK_DIR=$(pwd)

  pip install build --no-cache-dir

  # Build wheel distribution
  python -m build --wheel --outdir "${WORK_DIR}/${DIST_DIR}"

  # Copy requirements.txt to distribution
  cp requirements.txt "${WORK_DIR}/${DIST_DIR}/"

  # Copy source files to temp directory
  cp -r src/* "${TEMP_DIR}/"
  cp requirements.txt pyproject.toml README.md "${TEMP_DIR}/"

  # Package source code
  cd "${TEMP_DIR}"
  zip -r "${WORK_DIR}/${DIST_DIR}/${NAME}.zip" . -x "**/__pycache__/**" "**/*.pyc"
  cd "${WORK_DIR}"

  # Clean up
  rm -rf "${TEMP_DIR}"

else
  echo "Invalid mode: ${MODE}. Use 'binary' or 'package'"
  exit 1
fi

echo "Done! Output in ${DIST_DIR}/"

#!/bin/bash
set -euo pipefail

########################################################################
#                              CONSTANTS                               #
########################################################################
NAME="claia"

# Directories
DIST_DIR="dist"
WHL_DIR="whl"
BIN_DIR="bin"
EXPORT_DIR="export"
TEMP_DIR=$(mktemp -d)
WORK_DIR=$(pwd)

# Action flags (exclusive)
DO_WHL=0
DO_BIN=0
DO_EXPORT=0


########################################################################
#                                SETUP                                 #
########################################################################
# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-whl)
      DO_WHL=1; shift ;;
    --build-ubuntu-bin)
      DO_BIN=1; shift ;;
    --export)
      DO_EXPORT=1; shift ;;
    --dist-dir|-d)
      DIST_DIR="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--build-whl | --build-ubuntu-bin | --export] [--dist-dir DIR]"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--build-whl | --build-ubuntu-bin | --export] [--dist-dir DIR]" >&2
      exit 2 ;;
  esac
done

# Enforce exactly one action
ACTION_COUNT=$((DO_WHL + DO_BIN + DO_EXPORT))
if [[ $ACTION_COUNT -ne 1 ]]; then
  echo "Specify exactly one action: --build-whl | --build-ubuntu-bin | --export" >&2
  exit 2
fi

# Create version file in dist root (if CI_COMMIT_SHA present)
if [ -n "${CI_COMMIT_SHA:-}" ]; then
  mkdir -p "${DIST_DIR}"
  DATE=$(date +%Y%m%d)
  SHORT_HASH=${CI_COMMIT_SHA:0:7}
  echo "${DATE}-${SHORT_HASH}" > "${DIST_DIR}/version.txt"
fi

# Create build paths
WHL_PATH="${DIST_DIR}/${WHL_DIR}"
BIN_PATH="${DIST_DIR}/${BIN_DIR}"
EXPORT_PATH="${DIST_DIR}/${EXPORT_DIR}"


########################################################################
#                             BUILD WHEEL                              #
########################################################################
if [[ $DO_WHL -eq 1 ]]; then
  echo "Building wheel distribution..."
  mkdir -p "${WHL_PATH}"
  pip install --no-cache-dir build
  python -m build --wheel --outdir "${WHL_PATH}"


########################################################################
#                         BUILD UBUNTU BINARY                          #
########################################################################
elif [[ $DO_BIN -eq 1 ]]; then
  echo "Building Ubuntu binary (PyInstaller)..."
  mkdir -p "${BIN_PATH}"
  pip install --no-cache-dir build pyinstaller
  pip install --no-cache-dir .
  pyinstaller --onefile \
    --name "${NAME}" \
    --paths src \
    --distpath "${BIN_PATH}" \
    src/claia/__main__.py


########################################################################
#                              EXPORT ZIP                              #
########################################################################
elif [[ $DO_EXPORT -eq 1 ]]; then
  echo "Exporting source package..."
  mkdir -p "${EXPORT_PATH}"
  cp -r src/* "${TEMP_DIR}/"
  cp pyproject.toml README.md "${TEMP_DIR}/"
  cd "${TEMP_DIR}"
  zip -r "${WORK_DIR}/${EXPORT_PATH}/${NAME}.zip" . -x "**/__pycache__/**" "**/*.pyc"
  cd "${WORK_DIR}"
  rm -rf "${TEMP_DIR}"
fi


########################################################################
#                               CLEANUP                                #
########################################################################
echo "Done! Output in ${DIST_DIR}/"

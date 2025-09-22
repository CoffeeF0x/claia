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
DEB_DIR="deb"
EXPORT_DIR="export"
TEMP_DIR=$(mktemp -d)
WORK_DIR=$(pwd)

# Action flags (exclusive)
DO_WHL=0
DO_BIN=0
DO_EXPORT=0
DO_DEB=0


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
    --build-deb)
      DO_DEB=1; shift ;;
    --dist-dir|-d)
      DIST_DIR="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--build-whl | --build-ubuntu-bin | --build-deb | --export] [--dist-dir DIR]"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--build-whl | --build-ubuntu-bin | --build-deb | --export] [--dist-dir DIR]" >&2
      exit 2 ;;
  esac
done

# Enforce exactly one action
ACTION_COUNT=$((DO_WHL + DO_BIN + DO_EXPORT + DO_DEB))
if [[ $ACTION_COUNT -ne 1 ]]; then
  echo "Specify exactly one action: --build-whl | --build-ubuntu-bin | --build-deb | --export" >&2
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
DEB_PATH="${DIST_DIR}/${DEB_DIR}"


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


########################################################################
#                           BUILD DEBIAN PACKAGE                        #
########################################################################
elif [[ $DO_DEB -eq 1 ]]; then
  echo "Building Debian package (.deb)..."
  mkdir -p "${DEB_PATH}"

  # Ensure Ubuntu binary exists (build if missing)
  if [[ ! -f "${BIN_PATH}/${NAME}" ]]; then
    echo "PyInstaller binary not found at ${BIN_PATH}/${NAME}; building it first..."
    mkdir -p "${BIN_PATH}"
    pip install --no-cache-dir build pyinstaller
    pip install --no-cache-dir .
    pyinstaller --onefile \
      --name "${NAME}" \
      --paths src \
      --distpath "${BIN_PATH}" \
      src/claia/__main__.py
  fi

  # Derive version from pyproject.toml and optionally append git short hash
  PROJECT_VERSION=$(python - <<'PY'
import tomllib, sys
with open('pyproject.toml','rb') as f:
  data = tomllib.load(f)
print(data.get('project',{}).get('version','0.0.0'))
PY
)
  SHORT_HASH="${CI_COMMIT_SHA:-}"
  if [[ -n "$SHORT_HASH" ]]; then
    SHORT_HASH=${SHORT_HASH:0:7}
    PROJECT_VERSION="${PROJECT_VERSION}+git${SHORT_HASH}"
  fi

  ARCH=$(dpkg --print-architecture 2>/dev/null || echo amd64)
  PKGROOT="${TEMP_DIR}/pkgroot"
  mkdir -p "${PKGROOT}/DEBIAN" "${PKGROOT}/usr/bin" "${PKGROOT}/usr/share/doc/${NAME}"

  # Install files into package root
  install -m 0755 "${BIN_PATH}/${NAME}" "${PKGROOT}/usr/bin/${NAME}"
  # Docs
  if [[ -f LICENSE ]]; then cp -a LICENSE "${PKGROOT}/usr/share/doc/${NAME}/"; fi
  if [[ -f NOTICE ]]; then cp -a NOTICE "${PKGROOT}/usr/share/doc/${NAME}/"; fi
  if [[ -f README.md ]]; then cp -a README.md "${PKGROOT}/usr/share/doc/${NAME}/"; fi

  # Control file
  cat > "${PKGROOT}/DEBIAN/control" <<EOF
Package: ${NAME}
Version: ${PROJECT_VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Maintainer: ExoFox, LLC
Description: CLAIA Framework CLI
 A command-line interface for the CLAIA framework.
EOF

  # Build .deb
  DEB_FILE="${DEB_PATH}/${NAME}_${PROJECT_VERSION}_${ARCH}.deb"
  dpkg-deb --build --root-owner-group "${PKGROOT}" "${DEB_FILE}"
  echo "Built package: ${DEB_FILE}"
fi


########################################################################
#                               CLEANUP                                #
########################################################################
echo "Done! Output in ${DIST_DIR}/"

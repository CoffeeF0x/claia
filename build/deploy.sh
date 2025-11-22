#!/bin/bash
set -euo pipefail

########################################################################
#                              CONSTANTS                               #
########################################################################
NAME="claia"
SRC_DIR="src/claia"

# Directories
DIST_DIR="dist"
WHL_DIR="whl"
BIN_DIR="bin"
DEB_DIR="deb"
EXPORT_DIR="export"
TEMP_DIR=$(mktemp -d)
WORK_DIR=$(pwd)


########################################################################
#                              FUNCTIONS                               #
########################################################################

# Install pip packages if not already installed
install_pip_packages() {
  echo "Installing required pip packages: $*"
  pip install --no-cache-dir "$@"
}

# Create output directory
create_output_dir() {
  local dir_path="$1"
  echo "Creating output directory: ${dir_path}"
  mkdir -p "${dir_path}"
}

# Build PyInstaller binary
build_pyinstaller_binary() {
  local output_path="$1"
  echo "Building PyInstaller binary..."
  mkdir -p "${output_path}"
  install_pip_packages build pyinstaller
  pip install --no-cache-dir .
  pyinstaller --onefile \
    --name "${NAME}" \
    --paths src \
    --distpath "${output_path}" \
    "${SRC_DIR}/__main__.py"
}

# Build wheel distribution
build_wheel() {
  echo "Building wheel distribution..."
  create_output_dir "${WHL_PATH}"
  install_pip_packages build
  python -m build --wheel --outdir "${WHL_PATH}"
}

# Build Ubuntu binary
build_ubuntu_binary() {
  echo "Building Ubuntu binary (PyInstaller)..."
  build_pyinstaller_binary "${BIN_PATH}"
}

# Export source package
export_source() {
  echo "Exporting source package..."
  create_output_dir "${EXPORT_PATH}"
  cp -r src/* "${TEMP_DIR}/"
  cp pyproject.toml README.md "${TEMP_DIR}/"
  cd "${TEMP_DIR}"
  zip -r "${WORK_DIR}/${EXPORT_PATH}/${NAME}.zip" . -x "**/__pycache__/**" "**/*.pyc"
  cd "${WORK_DIR}"
  rm -rf "${TEMP_DIR}"
}

# Build Debian package
build_debian_package() {
  echo "Building Debian package (.deb)..."
  create_output_dir "${DEB_PATH}"

  # Ensure Ubuntu binary exists (build if missing)
  if [[ ! -f "${BIN_PATH}/${NAME}" ]]; then
    echo "PyInstaller binary not found at ${BIN_PATH}/${NAME}; building it first..."
    build_pyinstaller_binary "${BIN_PATH}"
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
}

# Show usage information
show_usage() {
  echo "Usage: $0 [--build-whl | --build-ubuntu-bin | --build-deb | --export] [--dist-dir DIR]"
}


########################################################################
#                                SETUP                                 #
########################################################################
# Parse arguments
ACTION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-whl)
      [[ -n "$ACTION" ]] && { echo "Error: Only one action allowed" >&2; exit 2; }
      ACTION="wheel"
      shift ;;
    --build-ubuntu-bin)
      [[ -n "$ACTION" ]] && { echo "Error: Only one action allowed" >&2; exit 2; }
      ACTION="binary"
      shift ;;
    --export)
      [[ -n "$ACTION" ]] && { echo "Error: Only one action allowed" >&2; exit 2; }
      ACTION="export"
      shift ;;
    --build-deb)
      [[ -n "$ACTION" ]] && { echo "Error: Only one action allowed" >&2; exit 2; }
      ACTION="debian"
      shift ;;
    --dist-dir|-d)
      DIST_DIR="$2"
      shift 2 ;;
    --help|-h)
      show_usage
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      show_usage >&2
      exit 2 ;;
  esac
done

# Enforce exactly one action was specified
if [[ -z "$ACTION" ]]; then
  echo "Error: Must specify exactly one action" >&2
  show_usage >&2
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
#                          EXECUTE BUILD ACTION                        #
########################################################################
case "$ACTION" in
  wheel)
    build_wheel ;;
  binary)
    build_ubuntu_binary ;;
  export)
    export_source ;;
  debian)
    build_debian_package ;;
  *)
    echo "Internal error: Unknown action '$ACTION'" >&2
    exit 1 ;;
esac


########################################################################
#                               CLEANUP                                #
########################################################################
echo "Done! Output in ${DIST_DIR}/"

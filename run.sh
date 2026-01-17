#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/venv-linux"
DEFAULT_CONFIG="${PROJECT_ROOT}/config/config.yaml"

if [ ! -d "${VENV_DIR}" ]; then
  echo "venv-linux not found. Run ./setup_venv.sh first." >&2
  exit 2
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

if [ "$#" -eq 0 ]; then
  echo "Select mode:"
  echo "  1) CLI"
  echo "  2) GUI"
  echo "  3) WEB"
  read -r -p "> " MODE

  read -r -p "Config path [${DEFAULT_CONFIG}]: " CONFIG_PATH
  if [ -z "${CONFIG_PATH}" ]; then
    CONFIG_PATH="${DEFAULT_CONFIG}"
  fi

  if [ "${MODE}" = "1" ] || [ "${MODE}" = "cli" ] || [ "${MODE}" = "CLI" ]; then
    python -m interfaces.cli.main --config "${CONFIG_PATH}" health-check
    exit $?
  fi

  if [ "${MODE}" = "2" ] || [ "${MODE}" = "gui" ] || [ "${MODE}" = "GUI" ]; then
    python -m interfaces.gui.main --config "${CONFIG_PATH}"
    exit $?
  fi

  if [ "${MODE}" = "3" ] || [ "${MODE}" = "web" ] || [ "${MODE}" = "WEB" ]; then
    python -m interfaces.web.main --config "${CONFIG_PATH}"
    exit $?
  fi

  echo "Unknown mode: ${MODE}" >&2
  exit 2
fi

MODE="$1"
shift

if [ "${MODE}" = "cli" ]; then
  python -m interfaces.cli.main "$@"
  exit $?
fi

if [ "${MODE}" = "gui" ]; then
  python -m interfaces.gui.main "$@"
  exit $?
fi

if [ "${MODE}" = "web" ]; then
  python -m interfaces.web.main "$@"
  exit $?
fi

echo "Usage:" >&2
echo "  ./run.sh                 # interactive"
echo "  ./run.sh cli [args...]   # run CLI (e.g. ./run.sh cli doctor)" >&2
echo "  ./run.sh gui [args...]   # run GUI" >&2
echo "  ./run.sh web [args...]   # run WEB (FastAPI)" >&2
exit 2

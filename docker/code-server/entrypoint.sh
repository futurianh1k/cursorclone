#!/usr/bin/env bash
set -euo pipefail

# Offline-friendly extension bootstrapper.
# - If /opt/extra-extensions contains *.vsix, install them at container start.
# - This avoids relying on external network/marketplace during runtime.
#
# Notes:
# - Installing an already-installed extension is harmless; code-server will skip or overwrite.
# - VSIX files should be provided by the operator (not committed), e.g. via host mount.

EXT_DIR="/opt/extra-extensions"

if [ -d "${EXT_DIR}" ]; then
  shopt -s nullglob
  for vsix in "${EXT_DIR}"/*.vsix; do
    echo "[entrypoint] Installing VSIX extension: ${vsix}"
    # Never fail hard on extension install to avoid blocking IDE startup.
    code-server --install-extension "${vsix}" || true
  done
  shopt -u nullglob
fi

# Optional: opencode.ai CLI (offline) mounted at /opt/opencode-cli
# If an executable "opencode" exists, prepend to PATH so VS Code extensions can invoke it.
if [ -x "/opt/opencode-cli/opencode" ]; then
  export PATH="/opt/opencode-cli:${PATH}"
  echo "[entrypoint] opencode CLI detected at /opt/opencode-cli/opencode (PATH updated)"
fi

exec dumb-init code-server "$@"


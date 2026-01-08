#!/usr/bin/env bash
set -euo pipefail

# Offline-friendly extension bootstrapper.
# - If /opt/extra-extensions contains *.vsix, install them at container start.
# - This avoids relying on external network/marketplace during runtime.
#
# Notes:
# - Installing an already-installed extension is harmless; code-server will skip or overwrite.
# - VSIX files should be provided by the operator (not committed), e.g. via host mount.

BUILTIN_EXT_DIR="/opt/builtin-extensions"
EXTRA_EXT_DIR="/opt/extra-extensions"

build_builtin_vsix_if_needed() {
  # Build built-in VSIX from source if python3 is available.
  # This avoids requiring python3 during docker build (heavy image can be offline-first).
  local src_root="/opt/builtin-vsix-src"
  local src="${src_root}/onprem-chat-panel"
  local out="${BUILTIN_EXT_DIR}/cursor-onprem.onprem-chat-panel-0.0.1.vsix"

  if [ ! -d "${src}" ]; then
    return 0
  fi
  if [ -f "${out}" ]; then
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[entrypoint] WARN: python3 not found; cannot build built-in VSIX from ${src_root}. (best-effort)"
    return 0
  fi

  mkdir -p "${BUILTIN_EXT_DIR}"
  echo "[entrypoint] Building built-in VSIX: ${out}"
  python3 - <<'PY'
import pathlib, zipfile

src = pathlib.Path("/opt/builtin-vsix-src/onprem-chat-panel")
out = pathlib.Path("/opt/builtin-extensions/cursor-onprem.onprem-chat-panel-0.0.1.vsix")
out.parent.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for p in src.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(src))

print("built", out)
PY
}

install_vsix_dir() {
  local dir="$1"
  if [ -d "${dir}" ]; then
    shopt -s nullglob
    for vsix in "${dir}"/*.vsix; do
      echo "[entrypoint] Installing VSIX extension: ${vsix}"
      # Never fail hard on extension install to avoid blocking IDE startup.
      code-server --install-extension "${vsix}" || true
    done
    shopt -u nullglob
  fi
}

# Install bundled VSIX first, then operator-provided VSIX (can override)
build_builtin_vsix_if_needed
install_vsix_dir "${BUILTIN_EXT_DIR}"
install_vsix_dir "${EXTRA_EXT_DIR}"

# Optional: opencode.ai CLI (offline) mounted at /opt/opencode-cli
# If an executable "opencode" exists, prepend to PATH so VS Code extensions can invoke it.
if [ -x "/opt/opencode-cli/opencode" ]; then
  export PATH="/opt/opencode-cli:${PATH}"
  echo "[entrypoint] opencode CLI detected at /opt/opencode-cli/opencode (PATH updated)"
fi

# Optional: Android SDK (offline) mounted at /opt/android-sdk
if [ -d "/opt/android-sdk" ]; then
  export ANDROID_HOME="/opt/android-sdk"
  export ANDROID_SDK_ROOT="/opt/android-sdk"

  # Common SDK subpaths (depending on how SDK is extracted/prepared)
  if [ -d "/opt/android-sdk/platform-tools" ]; then
    export PATH="/opt/android-sdk/platform-tools:${PATH}"
  fi
  if [ -d "/opt/android-sdk/cmdline-tools/latest/bin" ]; then
    export PATH="/opt/android-sdk/cmdline-tools/latest/bin:${PATH}"
  fi
  if [ -d "/opt/android-sdk/cmdline-tools/bin" ]; then
    export PATH="/opt/android-sdk/cmdline-tools/bin:${PATH}"
  fi
  echo "[entrypoint] Android SDK detected at /opt/android-sdk (ANDROID_HOME set)"
fi

exec dumb-init code-server "$@"


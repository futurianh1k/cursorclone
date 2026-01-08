from __future__ import annotations

from pathlib import Path


def test_onprem_chat_panel_vsix_source_exists():
    repo = Path(__file__).resolve().parents[3]
    src = repo / "docker" / "code-server" / "builtin-vsix" / "onprem-chat-panel"
    assert (src / "extension" / "package.json").exists()
    assert (src / "extension" / "extension.js").exists()
    assert (src / "extension.vsixmanifest").exists()
    assert (src / "[Content_Types].xml").exists()


def test_dockerfiles_reference_bundled_vsix_source():
    repo = Path(__file__).resolve().parents[3]
    dockerfile = (repo / "docker" / "code-server" / "Dockerfile").read_text(encoding="utf-8")
    dockerfile_heavy = (repo / "docker" / "code-server" / "Dockerfile.heavy").read_text(encoding="utf-8")

    assert "builtin-vsix/onprem-chat-panel" in dockerfile
    assert "builtin-vsix/onprem-chat-panel" in dockerfile_heavy
    assert "/opt/builtin-vsix-src" in dockerfile
    assert "/opt/builtin-vsix-src" in dockerfile_heavy


def test_entrypoint_installs_bundled_and_extra_vsix():
    repo = Path(__file__).resolve().parents[3]
    entrypoint = (repo / "docker" / "code-server" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "BUILTIN_EXT_DIR" in entrypoint
    assert "EXTRA_EXT_DIR" in entrypoint
    assert "install_vsix_dir" in entrypoint
    assert "build_builtin_vsix_if_needed" in entrypoint


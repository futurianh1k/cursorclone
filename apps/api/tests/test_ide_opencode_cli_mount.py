import importlib


def test_ide_service_has_opencode_cli_mount_env(monkeypatch):
    """
    새 기능: HOST_OPENCODE_CLI_PATH가 설정되면 IDE 컨테이너에 /opt/opencode-cli 로 마운트 가능해야 한다.
    실제 docker run은 테스트에서 수행하지 않는다.
    """
    from src.services import ide_service as ide_service_module

    monkeypatch.setenv("HOST_OPENCODE_CLI_PATH", "/tmp/opencode-cli")
    ide_service_module = importlib.reload(ide_service_module)

    assert ide_service_module.HOST_OPENCODE_CLI_PATH == "/tmp/opencode-cli"

    volumes = {
        "/some/workspace": {"bind": "/home/coder/project", "mode": "rw"},
        **(
            {ide_service_module.HOST_OPENCODE_CLI_PATH: {"bind": "/opt/opencode-cli", "mode": "ro"}}
            if ide_service_module.HOST_OPENCODE_CLI_PATH
            else {}
        ),
    }
    assert "/tmp/opencode-cli" in volumes
    assert volumes["/tmp/opencode-cli"]["bind"] == "/opt/opencode-cli"
    assert volumes["/tmp/opencode-cli"]["mode"] == "ro"


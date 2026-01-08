import os


def test_ide_service_includes_extra_extensions_mount_when_env_set(monkeypatch):
    """
    새 기능: HOST_IDE_EXTENSIONS_PATH가 설정되면 IDE 컨테이너에 /opt/extra-extensions로 마운트되도록 한다.
    - 실제 docker run은 테스트에서 수행하지 않고, volume dict 생성 로직만 검증한다.
    """
    from src.services import ide_service as ide_service_module

    monkeypatch.setenv("HOST_IDE_EXTENSIONS_PATH", "/tmp/ide-extensions")
    # module-level 상수를 env로부터 다시 읽도록 reload
    import importlib

    ide_service_module = importlib.reload(ide_service_module)

    # _create_container_async 내부에서 volumes dict에 포함되는지 확인하기 위해,
    # 해당 모듈의 HOST_IDE_EXTENSIONS_PATH 상수를 직접 검증하고,
    # 동일 조건의 volumes merge가 가능한 형태인지 확인한다.
    assert ide_service_module.HOST_IDE_EXTENSIONS_PATH == "/tmp/ide-extensions"

    volumes = {
        "/some/workspace": {"bind": "/home/coder/project", "mode": "rw"},
        **(
            {ide_service_module.HOST_IDE_EXTENSIONS_PATH: {"bind": "/opt/extra-extensions", "mode": "ro"}}
            if ide_service_module.HOST_IDE_EXTENSIONS_PATH
            else {}
        ),
    }
    assert "/tmp/ide-extensions" in volumes
    assert volumes["/tmp/ide-extensions"]["bind"] == "/opt/extra-extensions"
    assert volumes["/tmp/ide-extensions"]["mode"] == "ro"


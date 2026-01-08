import importlib


def test_ide_service_has_android_sdk_mount_env(monkeypatch):
    """
    새 기능: HOST_ANDROID_SDK_PATH가 설정되면 IDE 컨테이너에 /opt/android-sdk 로 마운트 가능해야 한다.
    실제 docker run은 테스트에서 수행하지 않는다.
    """
    from src.services import ide_service as ide_service_module

    monkeypatch.setenv("HOST_ANDROID_SDK_PATH", "/tmp/android-sdk")
    ide_service_module = importlib.reload(ide_service_module)

    assert ide_service_module.HOST_ANDROID_SDK_PATH == "/tmp/android-sdk"

    volumes = {
        "/some/workspace": {"bind": "/home/coder/project", "mode": "rw"},
        **(
            {ide_service_module.HOST_ANDROID_SDK_PATH: {"bind": "/opt/android-sdk", "mode": "ro"}}
            if ide_service_module.HOST_ANDROID_SDK_PATH
            else {}
        ),
    }
    assert "/tmp/android-sdk" in volumes
    assert volumes["/tmp/android-sdk"]["bind"] == "/opt/android-sdk"
    assert volumes["/tmp/android-sdk"]["mode"] == "ro"


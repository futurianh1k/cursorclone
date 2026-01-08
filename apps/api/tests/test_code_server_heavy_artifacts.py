from pathlib import Path


def test_code_server_heavy_files_exist():
    """
    신규 기능(무거운 code-server 이미지 옵션): 관련 산출물이 레포에 존재해야 한다.
    """
    # apps/api/tests/.. -> apps/api -> apps -> repo root
    repo = Path(__file__).resolve().parents[3]
    assert (repo / "docker" / "code-server" / "Dockerfile.heavy").exists()
    assert (repo / "docs" / "0028-code-server-heavy-image.md").exists()


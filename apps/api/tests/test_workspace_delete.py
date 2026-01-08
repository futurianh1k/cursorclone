"""
워크스페이스 삭제 기능 테스트

사용법:
    cd apps/api
    pytest tests/test_workspace_delete.py -v
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 테스트 환경 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.utils.filesystem import (
    delete_workspace_directory,
    get_workspace_root,
)


class TestWorkspaceDelete:
    """워크스페이스 삭제 기능 테스트"""

    def test_delete_workspace_directory_path_validation(self, tmp_path):
        """경로 검증 테스트"""
        # /workspaces 외부 경로는 삭제 불가
        external_path = tmp_path / "external"
        external_path.mkdir()

        with pytest.raises(ValueError, match="Cannot delete path outside /workspaces"):
            delete_workspace_directory(external_path)

    def test_delete_workspace_directory_root_protection(self):
        """루트 디렉토리 보호 테스트"""
        workspaces_root = Path("/workspaces")

        # /workspaces 자체는 삭제 불가
        with pytest.raises(ValueError, match="Cannot delete /workspaces root directory"):
            delete_workspace_directory(workspaces_root)

    @patch("shutil.rmtree")
    def test_delete_workspace_directory_success(self, mock_rmtree, tmp_path):
        """정상 삭제 테스트 (Mock)"""
        # /workspaces/test-ws 경로 시뮬레이션
        test_workspace = Path("/workspaces/test-ws")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_dir", return_value=True):
                with patch.object(Path, "resolve", autospec=True) as mock_resolve:
                    # Path.resolve를 패치하면 /workspaces base도 동일하게 패치되므로
                    # base_resolved는 /workspaces, 대상은 /workspaces/test-ws 로 분리되도록 side_effect를 사용한다.
                    def _resolve_side_effect(self):
                        if str(self) == "/workspaces":
                            return Path("/workspaces")
                        return test_workspace

                    mock_resolve.side_effect = _resolve_side_effect

                    # Mock으로 실제 삭제는 하지 않음
                    delete_workspace_directory(test_workspace)

                    # rmtree가 호출되었는지 확인
                    mock_rmtree.assert_called_once_with(test_workspace)

    def test_delete_workspace_directory_not_exists(self):
        """존재하지 않는 디렉토리 삭제 (에러 없음)"""
        non_existent = Path("/workspaces/non-existent")

        # 존재하지 않는 경우 에러 없이 리턴
        try:
            delete_workspace_directory(non_existent)
        except Exception as e:
            pytest.fail(f"Should not raise exception for non-existent directory: {e}")

    def test_delete_workspace_directory_not_directory(self):
        """디렉토리가 아닌 경로 삭제"""
        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "is_dir", return_value=False):
                with patch.object(Path, "resolve", autospec=True) as mock_resolve:
                    test_file = Path("/workspaces/test-file.txt")
                    def _resolve_side_effect(self):
                        if str(self) == "/workspaces":
                            return Path("/workspaces")
                        return test_file

                    mock_resolve.side_effect = _resolve_side_effect

                    with pytest.raises(ValueError, match="Path is not a directory"):
                        delete_workspace_directory(test_file)


class TestWorkspaceDeleteAPI:
    """워크스페이스 삭제 API 테스트 (통합 테스트용)"""

    @pytest.mark.asyncio
    async def test_delete_workspace_api_integration(self):
        """
        API 통합 테스트 (실제 서버 실행 필요)

        실제 환경에서 테스트하려면:
        1. API 서버 실행
        2. 테스트 워크스페이스 생성
        3. 삭제 API 호출
        4. 삭제 확인
        """
        # TODO: FastAPI TestClient를 사용한 통합 테스트
        # from fastapi.testclient import TestClient
        # from src.main import app
        # client = TestClient(app)
        # response = client.delete("/api/workspaces/ws_test")
        # assert response.status_code == 204
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

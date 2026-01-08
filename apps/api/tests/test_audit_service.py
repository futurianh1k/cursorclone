"""
감사 로그 서비스 (src/services/audit_service.py) 테스트
"""

import pytest
import hashlib
from unittest.mock import MagicMock, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.audit_service import AuditService


@pytest.fixture
def mock_db_session():
    """Mock DB 세션"""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


class TestAuditService:
    """AuditService.log() 테스트 (DB 저장 + 해시 저장)"""

    @pytest.mark.asyncio
    async def test_log_saves_hashes(self, mock_db_session):
        instruction = "비밀 정보가 포함된 프롬프트"
        response = "민감한 응답 내용"
        patch_content = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"

        await AuditService.log(
            db=mock_db_session,
            user_id="test-user",
            workspace_id="test-ws",
            action="chat",
            instruction=instruction,
            response=response,
            patch=patch_content,
            tokens_used=123,
        )

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

        audit_log = mock_db_session.add.call_args[0][0]
        assert audit_log.instruction_hash == hashlib.sha256(instruction.encode()).hexdigest()
        assert audit_log.response_hash == hashlib.sha256(response.encode()).hexdigest()
        assert audit_log.patch_hash == hashlib.sha256(patch_content.encode()).hexdigest()
        assert audit_log.tokens_used == 123

    @pytest.mark.asyncio
    async def test_log_handles_db_error(self, mock_db_session):
        mock_db_session.commit.side_effect = Exception("DB connection failed")
        res = await AuditService.log(
            db=mock_db_session,
            user_id="test-user",
            workspace_id="test-ws",
            action="error_test",
        )
        assert res is None
        mock_db_session.rollback.assert_called_once()


class TestAuditServiceHashing:
    """해시 함수 테스트"""

    def test_sha256_hash_consistency(self):
        """SHA-256 해시 일관성 테스트"""
        text = "테스트 문자열"
        
        hash1 = hashlib.sha256(text.encode()).hexdigest()
        hash2 = hashlib.sha256(text.encode()).hexdigest()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256은 64자리 16진수

    def test_different_inputs_different_hashes(self):
        """다른 입력에 다른 해시 테스트"""
        text1 = "입력 1"
        text2 = "입력 2"
        
        hash1 = hashlib.sha256(text1.encode()).hexdigest()
        hash2 = hashlib.sha256(text2.encode()).hexdigest()
        
        assert hash1 != hash2

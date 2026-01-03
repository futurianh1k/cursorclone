"""
감사 로그 서비스 (audit_service.py) 테스트
"""

import pytest
import hashlib
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.audit_service import AuditService


class TestAuditService:
    """AuditService 테스트"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock DB 세션"""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def audit_service(self, mock_db_session):
        """AuditService 인스턴스"""
        return AuditService(db_session=mock_db_session)

    @pytest.fixture
    def audit_service_no_db(self):
        """DB 없는 AuditService 인스턴스"""
        return AuditService(db_session=None)

    @pytest.mark.asyncio
    async def test_log_audit_event_with_db(self, audit_service, mock_db_session):
        """DB에 감사 로그 저장 테스트"""
        await audit_service.log_audit_event(
            user_id="test-user",
            workspace_id="test-ws",
            action="explain",
            instruction="코드를 설명해줘",
            response_content="이 코드는...",
            tokens_used=100,
        )
        
        # DB에 추가되었는지 확인
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_audit_event_hashes_content(self, audit_service, mock_db_session):
        """민감 정보가 해시로 저장되는지 테스트"""
        instruction = "비밀 정보가 포함된 프롬프트"
        response = "민감한 응답 내용"
        
        await audit_service.log_audit_event(
            user_id="test-user",
            workspace_id="test-ws",
            action="chat",
            instruction=instruction,
            response_content=response,
        )
        
        # add에 전달된 모델 확인
        call_args = mock_db_session.add.call_args
        audit_log = call_args[0][0]
        
        # 해시가 저장되어야 함
        expected_instruction_hash = hashlib.sha256(instruction.encode()).hexdigest()
        expected_response_hash = hashlib.sha256(response.encode()).hexdigest()
        
        assert audit_log.instruction_hash == expected_instruction_hash
        assert audit_log.response_hash == expected_response_hash

    @pytest.mark.asyncio
    async def test_log_audit_event_without_db(self, audit_service_no_db, caplog):
        """DB 없이 콘솔 로깅 테스트"""
        import logging
        
        with caplog.at_level(logging.INFO):
            await audit_service_no_db.log_audit_event(
                user_id="test-user",
                workspace_id="test-ws",
                action="explain",
            )
        
        # 경고 메시지가 로그에 있어야 함
        assert any("without a DB session" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_log_audit_event_with_patch(self, audit_service, mock_db_session):
        """패치 해시 저장 테스트"""
        patch_content = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
        
        await audit_service.log_audit_event(
            user_id="test-user",
            workspace_id="test-ws",
            action="patch_apply",
            patch_content=patch_content,
        )
        
        call_args = mock_db_session.add.call_args
        audit_log = call_args[0][0]
        
        expected_patch_hash = hashlib.sha256(patch_content.encode()).hexdigest()
        assert audit_log.patch_hash == expected_patch_hash

    @pytest.mark.asyncio
    async def test_log_audit_event_none_values(self, audit_service, mock_db_session):
        """None 값 처리 테스트"""
        await audit_service.log_audit_event(
            user_id="test-user",
            workspace_id="test-ws",
            action="view",
            instruction=None,
            response_content=None,
            patch_content=None,
            tokens_used=None,
        )
        
        call_args = mock_db_session.add.call_args
        audit_log = call_args[0][0]
        
        assert audit_log.instruction_hash is None
        assert audit_log.response_hash is None
        assert audit_log.patch_hash is None
        assert audit_log.tokens_used is None

    @pytest.mark.asyncio
    async def test_log_audit_event_db_error(self, audit_service, mock_db_session, caplog):
        """DB 에러 처리 테스트"""
        import logging
        
        mock_db_session.commit.side_effect = Exception("DB connection failed")
        
        with caplog.at_level(logging.ERROR):
            await audit_service.log_audit_event(
                user_id="test-user",
                workspace_id="test-ws",
                action="error_test",
            )
        
        # 에러가 로그에 있어야 함
        assert any("Failed to save audit log" in record.message for record in caplog.records)


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


class TestGetAuditService:
    """get_audit_service 의존성 테스트"""

    @pytest.mark.asyncio
    async def test_get_audit_service_with_db(self):
        """DB 세션이 주입되는지 테스트"""
        from src.services.audit_service import get_audit_service
        
        mock_db = AsyncMock()
        
        # FastAPI Depends 시뮬레이션
        service = await get_audit_service(db=mock_db)
        
        assert isinstance(service, AuditService)
        assert service.db_session is mock_db

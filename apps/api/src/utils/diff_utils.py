"""
Diff Utils - Unified Diff 파서/검증/적용 (Python 포팅)
Task C: Diff 유틸 Python 포팅
TypeScript 버전: packages/diff-utils/src/index.ts
"""

import os
import re
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
from ..utils.filesystem import ALLOWED_EXTENSIONS, read_file_content, write_file_content, validate_path

# 최대 패치 크기 (바이트)
MAX_PATCH_SIZE = 1_000_000  # 1MB

# 최대 파일 수
MAX_FILES = 100


class PatchFile:
    """패치 파일 정보"""
    def __init__(self, old_path: str, new_path: str, hunks: List["PatchHunk"]):
        self.old_path = old_path
        self.new_path = new_path
        self.hunks = hunks


class PatchHunk:
    """패치 hunk 정보"""
    def __init__(
        self,
        old_start: int,
        old_lines: int,
        new_start: int,
        new_lines: int,
        lines: List["HunkLine"],
    ):
        self.old_start = old_start
        self.old_lines = old_lines
        self.new_start = new_start
        self.new_lines = new_lines
        self.lines = lines


class HunkLine:
    """Hunk 라인"""
    def __init__(self, line_type: str, content: str):
        self.type = line_type  # "+", "-", " ", "\\"
        self.content = content


class ConflictInfo:
    """충돌 정보"""
    def __init__(self, file: str, hunk_index: int, reason: str):
        self.file = file
        self.hunk_index = hunk_index
        self.reason = reason


class PatchValidationResult:
    """패치 검증 결과"""
    def __init__(
        self,
        valid: bool,
        reason: Optional[str] = None,
        files: Optional[List[str]] = None,
        parsed_files: Optional[List[PatchFile]] = None,
    ):
        self.valid = valid
        self.reason = reason
        self.files = files or []
        self.parsed_files = parsed_files or []


class ApplyPatchResult:
    """패치 적용 결과"""
    def __init__(
        self,
        success: bool,
        content: str,
        applied_hunks: int,
        conflicts: Optional[List[ConflictInfo]] = None,
    ):
        self.success = success
        self.content = content
        self.applied_hunks = applied_hunks
        self.conflicts = conflicts or []


def parse_unified_diff(patch: str) -> List[PatchFile]:
    """
    unified diff 문자열을 파싱합니다.
    
    Args:
        patch: unified diff 문자열
        
    Returns:
        파싱된 파일 목록
    """
    files: List[PatchFile] = []
    lines = patch.split("\n")
    
    i = 0
    while i < len(lines):
        # 파일 헤더 찾기: --- a/path 또는 +++ b/path
        if lines[i].startswith("--- "):
            old_path = _extract_path(lines[i], "--- ")
            i += 1
            
            if i >= len(lines) or not lines[i].startswith("+++ "):
                raise ValueError(f"Invalid diff format: missing +++ after --- at line {i + 1}")
            
            new_path = _extract_path(lines[i], "+++ ")
            i += 1
            
            # hunk 찾기
            hunks: List[PatchHunk] = []
            while i < len(lines) and not lines[i].startswith("--- "):
                if lines[i].startswith("@@ "):
                    hunk, next_index = _parse_hunk(lines, i)
                    hunks.append(hunk)
                    i = next_index
                else:
                    i += 1
            
            files.append(PatchFile(old_path, new_path, hunks))
        else:
            i += 1
    
    return files


def _extract_path(line: str, prefix: str) -> str:
    """경로 추출 (--- a/path 또는 +++ b/path에서)"""
    path = line[len(prefix):]
    # "a/" 또는 "b/" 제거
    if path.startswith("a/"):
        return path[2:]
    if path.startswith("b/"):
        return path[2:]
    return path


def _parse_hunk(lines: List[str], start_index: int) -> Tuple[PatchHunk, int]:
    """hunk 파싱 (@@ -start,count +start,count @@)"""
    header_line = lines[start_index]
    match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header_line)
    
    if not match:
        raise ValueError(f"Invalid hunk header at line {start_index + 1}: {header_line}")
    
    old_start = int(match.group(1))
    old_lines = int(match.group(2)) if match.group(2) else 1
    new_start = int(match.group(3))
    new_lines = int(match.group(4)) if match.group(4) else 1
    
    hunk_lines: List[HunkLine] = []
    i = start_index + 1
    
    while i < len(lines) and not lines[i].startswith("@@ ") and not lines[i].startswith("--- "):
        line = lines[i]
        
        if line.startswith("+"):
            hunk_lines.append(HunkLine("+", line[1:]))
        elif line.startswith("-"):
            hunk_lines.append(HunkLine("-", line[1:]))
        elif line.startswith("\\"):
            hunk_lines.append(HunkLine("\\", line[1:]))
        else:
            # 공백 또는 컨텍스트 라인
            hunk_lines.append(HunkLine(" ", line[1:] if line.startswith(" ") else line))
        
        i += 1
    
    return PatchHunk(old_start, old_lines, new_start, new_lines, hunk_lines), i


def validate_patch(patch: str, workspace_root: Optional[Path] = None) -> PatchValidationResult:
    """
    패치를 검증합니다.
    
    Args:
        patch: unified diff 문자열
        workspace_root: 워크스페이스 루트 경로 (선택)
        
    Returns:
        검증 결과
    """
    # 1. 빈 패치 검증
    if not patch or len(patch.strip()) < 10:
        return PatchValidationResult(valid=False, reason="empty_or_too_small")
    
    # 2. 패치 크기 검증
    if len(patch) > MAX_PATCH_SIZE:
        return PatchValidationResult(valid=False, reason="patch_too_large")
    
    # 3. 경로 탈출 검증 (기본)
    if "../" in patch or "..\\" in patch:
        return PatchValidationResult(valid=False, reason="path_traversal_suspected")
    
    # 4. diff 파싱 시도
    try:
        parsed_files = parse_unified_diff(patch)
    except Exception as e:
        return PatchValidationResult(
            valid=False,
            reason="invalid_diff_format",
            files=[],
        )
    
    # 5. 파일 수 제한
    if len(parsed_files) > MAX_FILES:
        return PatchValidationResult(
            valid=False,
            reason="too_many_files",
            files=[f.new_path for f in parsed_files],
        )
    
    # 6. 각 파일 검증
    files: List[str] = []
    for file_info in parsed_files:
        # 경로 정규화 및 검증
        try:
            normalized_new = _normalize_path(file_info.new_path)
            
            # 워크스페이스 루트 검증 (제공된 경우)
            if workspace_root:
                full_path = workspace_root / normalized_new
                resolved = full_path.resolve()
                root_resolved = workspace_root.resolve()
                
                if not str(resolved).startswith(str(root_resolved)):
                    return PatchValidationResult(
                        valid=False,
                        reason="path_outside_workspace",
                        files=[normalized_new],
                    )
            
            # 확장자 검증
            ext = Path(normalized_new).suffix.lower()
            if ext and ext not in ALLOWED_EXTENSIONS:
                return PatchValidationResult(
                    valid=False,
                    reason="extension_not_allowed",
                    files=[normalized_new],
                )
            
            files.append(normalized_new)
        except ValueError:
            return PatchValidationResult(
                valid=False,
                reason="invalid_path",
                files=[file_info.new_path],
            )
    
    return PatchValidationResult(
        valid=True,
        files=files,
        parsed_files=parsed_files,
    )


def _normalize_path(path: str) -> str:
    """경로 정규화 및 검증"""
    if not path:
        raise ValueError("Empty path")
    
    # 절대 경로 금지
    if os.path.isabs(path):
        raise ValueError("Absolute paths are not allowed")
    
    # 경로 탈출 시도 차단
    if "../" in path or "..\\" in path:
        raise ValueError("Path traversal detected")
    
    # 정규화
    normalized = os.path.normpath(path).replace("\\", "/")
    
    return normalized


def apply_patch_to_text(original: str, patch: str) -> ApplyPatchResult:
    """
    패치를 텍스트에 적용합니다.
    
    Args:
        original: 원본 텍스트
        patch: unified diff 문자열
        
    Returns:
        적용 결과
    """
    original_lines = original.split("\n")
    
    # 패치 파싱
    parsed_files = parse_unified_diff(patch)
    
    if len(parsed_files) == 0:
        return ApplyPatchResult(
            success=False,
            content=original,
            applied_hunks=0,
            conflicts=[ConflictInfo("", 0, "no_files_in_patch")],
        )
    
    # 단일 파일 패치만 지원 (현재)
    file_info = parsed_files[0]
    conflicts: List[ConflictInfo] = []
    applied_hunks = 0
    
    # 역순으로 적용 (라인 번호 변경 방지)
    hunks = list(reversed(file_info.hunks))
    result_lines = original_lines.copy()
    
    for hunk_index, hunk in enumerate(hunks):
        start_line = hunk.old_start - 1  # 0-based index
        
        # 범위 검증
        if start_line < 0 or start_line >= len(result_lines):
            conflicts.append(
                ConflictInfo(
                    file_info.new_path,
                    hunk_index,
                    "invalid_line_range",
                )
            )
            continue
        
        # 컨텍스트 매칭 확인
        context_match, reason = _check_context_match(result_lines, hunk, start_line)
        if not context_match:
            conflicts.append(
                ConflictInfo(
                    file_info.new_path,
                    hunk_index,
                    reason or "context_mismatch",
                )
            )
            continue
        
        # 패치 적용
        # 1. 기존 라인 제거
        lines_to_remove = hunk.old_lines
        result_lines[start_line:start_line + lines_to_remove] = []
        
        # 2. 새 라인 삽입
        new_lines: List[str] = []
        for line in hunk.lines:
            if line.type == "+":
                new_lines.append(line.content)
            elif line.type == " ":
                new_lines.append(line.content)
            # "-" 타입은 이미 제거됨
        
        result_lines[start_line:start_line] = new_lines
        applied_hunks += 1
    
    return ApplyPatchResult(
        success=len(conflicts) == 0,
        content="\n".join(result_lines),
        applied_hunks=applied_hunks,
        conflicts=conflicts if conflicts else None,
    )


def _check_context_match(
    lines: List[str],
    hunk: PatchHunk,
    start_line: int,
) -> Tuple[bool, Optional[str]]:
    """컨텍스트 매칭 확인"""
    # 범위 확인
    if start_line < 0:
        return False, "start_line_negative"
    
    if start_line + hunk.old_lines > len(lines):
        return False, "range_out_of_bounds"
    
    # 라인 매칭 확인
    # "-" 라인과 " " 라인만 확인 (실제 파일에 있어야 하는 라인)
    line_index = start_line
    
    for hunk_line in hunk.lines:
        if hunk_line.type == "-":
            # 제거될 라인 - 실제 파일에서 확인
            if line_index >= len(lines):
                return False, "line_out_of_range"
            
            expected = hunk_line.content
            actual = lines[line_index]
            
            if actual != expected:
                return False, f"line_mismatch_at_line_{line_index + 1}: expected '{expected}', got '{actual}'"
            
            line_index += 1
        elif hunk_line.type == " ":
            # 컨텍스트 라인은 일치해야 함
            # 빈 라인은 무시 (파일 끝의 빈 라인)
            if hunk_line.content == "" and line_index >= len(lines):
                # 파일 끝의 빈 라인은 OK
                continue
            
            if line_index >= len(lines):
                return False, "context_out_of_range"
            
            expected = hunk_line.content
            actual = lines[line_index]
            
            if actual != expected:
                return False, f"context_mismatch_at_line_{line_index + 1}: expected '{expected}', got '{actual}'"
            
            line_index += 1
        # "+" 타입은 새로 추가되므로 스킵 (라인 인덱스 증가 안 함)
    
    return True, None


def apply_patch_to_file(
    file_path: Path,
    file_patch: "PatchFile",
    workspace_root: Path,
) -> ApplyPatchResult:
    """
    패치를 파일에 적용합니다.
    
    Args:
        file_path: 파일 경로 (workspace 기준 상대 경로)
        file_patch: 해당 파일의 패치 정보
        workspace_root: 워크스페이스 루트
        
    Returns:
        적용 결과
    """
    # 파일 경로 검증
    full_path = validate_path(str(file_path), workspace_root)
    
    # 파일 읽기
    try:
        original_content, _ = read_file_content(full_path)
    except FileNotFoundError:
        # 새 파일인 경우 빈 문자열로 시작
        original_content = ""
    except Exception as e:
        return ApplyPatchResult(
            success=False,
            content="",
            applied_hunks=0,
            conflicts=[ConflictInfo(str(file_path), 0, f"file_read_error: {e}")],
        )
    
    # 해당 파일의 패치만 추출하여 적용
    # 단일 파일 패치 생성
    single_file_patch = _create_single_file_patch(file_patch)
    
    # 패치 적용
    result = apply_patch_to_text(original_content, single_file_patch)
    
    # 성공 시 파일 쓰기
    if result.success:
        try:
            write_file_content(full_path, result.content, create_backup=True)
        except Exception as e:
            return ApplyPatchResult(
                success=False,
                content=result.content,
                applied_hunks=result.applied_hunks,
                conflicts=[ConflictInfo(str(file_path), 0, f"file_write_error: {e}")],
            )
    
    return result


def _create_single_file_patch(file_patch: PatchFile) -> str:
    """단일 파일 패치 문자열 생성"""
    lines = [f"--- a/{file_patch.old_path}", f"+++ b/{file_patch.new_path}"]
    
    for hunk in file_patch.hunks:
        # Hunk 헤더
        old_count = hunk.old_lines if hunk.old_lines > 0 else 1
        new_count = hunk.new_lines if hunk.new_lines > 0 else 1
        lines.append(f"@@ -{hunk.old_start},{old_count} +{hunk.new_start},{new_count} @@")
        
        # Hunk 라인
        for line in hunk.lines:
            if line.type == "+":
                lines.append(f"+{line.content}")
            elif line.type == "-":
                lines.append(f"-{line.content}")
            elif line.type == "\\":
                lines.append(f"\\{line.content}")
            else:
                lines.append(f" {line.content}")
    
    return "\n".join(lines)

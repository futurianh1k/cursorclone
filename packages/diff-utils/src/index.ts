/**
 * Diff Utils - Unified Diff 파서/검증/적용
 * Task C: Diff 유틸 구현
 * 
 * 기능:
 * - unified diff 파싱
 * - 보안 검증 (경로 탈출, 확장자 allowlist, 크기 제한)
 * - 패치 적용
 */

import * as path from "path";

// ============================================================
// 타입 정의
// ============================================================

export interface PatchFile {
  /** 원본 파일 경로 */
  oldPath: string;
  /** 새 파일 경로 */
  newPath: string;
  /** 변경 사항 (hunk) */
  hunks: PatchHunk[];
}

export interface PatchHunk {
  /** 시작 라인 (원본) */
  oldStart: number;
  /** 라인 수 (원본) */
  oldLines: number;
  /** 시작 라인 (새 파일) */
  newStart: number;
  /** 라인 수 (새 파일) */
  newLines: number;
  /** 변경 내용 */
  lines: HunkLine[];
}

export interface HunkLine {
  /** 라인 타입 */
  type: "+" | "-" | " " | "\\";
  /** 라인 내용 (타입 문자 제외) */
  content: string;
}

export interface PatchValidationResult {
  valid: boolean;
  reason?: string;
  files?: string[];
  parsedFiles?: PatchFile[];
}

export interface ApplyPatchResult {
  success: boolean;
  content: string;
  appliedHunks: number;
  conflicts?: ConflictInfo[];
}

export interface ConflictInfo {
  file: string;
  hunkIndex: number;
  reason: string;
}

// ============================================================
// 설정
// ============================================================

/** 허용된 파일 확장자 (allowlist) */
export const ALLOWED_EXTENSIONS = new Set([
  // 프로그래밍 언어
  ".py", ".js", ".ts", ".tsx", ".jsx",
  ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
  ".rb", ".php", ".swift", ".kt", ".scala",
  ".cs", ".vb", ".fs",
  
  // 설정/마크업
  ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
  ".md", ".txt", ".html", ".css", ".scss", ".sass",
  ".xml", ".svg",
  
  // 기타
  ".sql", ".sh", ".bash", ".zsh", ".fish",
  ".dockerfile", ".dockerignore",
  ".gitignore", ".gitattributes",
  ".env", ".env.example",
]);

/** 최대 패치 크기 (바이트) */
export const MAX_PATCH_SIZE = 1_000_000; // 1MB

/** 최대 파일 크기 (바이트) */
export const MAX_FILE_SIZE = 10_000_000; // 10MB

/** 최대 파일 수 */
export const MAX_FILES = 100;

// ============================================================
// Unified Diff 파서
// ============================================================

/**
 * unified diff 문자열을 파싱합니다.
 * 
 * @param patch unified diff 문자열
 * @returns 파싱된 파일 목록
 */
export function parseUnifiedDiff(patch: string): PatchFile[] {
  const files: PatchFile[] = [];
  const lines = patch.split("\n");
  
  let i = 0;
  while (i < lines.length) {
    // 파일 헤더 찾기: --- a/path 또는 +++ b/path
    if (lines[i].startsWith("--- ")) {
      const oldPath = extractPath(lines[i], "--- ");
      i++;
      
      if (i >= lines.length || !lines[i].startsWith("+++ ")) {
        throw new Error(`Invalid diff format: missing +++ after --- at line ${i + 1}`);
      }
      
      const newPath = extractPath(lines[i], "+++ ");
      i++;
      
      // hunk 찾기
      const hunks: PatchHunk[] = [];
      while (i < lines.length && !lines[i].startsWith("--- ")) {
        if (lines[i].startsWith("@@ ")) {
          const hunk = parseHunk(lines, i);
          hunks.push(hunk.hunk);
          i = hunk.nextIndex;
        } else {
          i++;
        }
      }
      
      files.push({
        oldPath,
        newPath,
        hunks,
      });
    } else {
      i++;
    }
  }
  
  return files;
}

/**
 * 경로 추출 (--- a/path 또는 +++ b/path에서)
 */
function extractPath(line: string, prefix: string): string {
  const path = line.slice(prefix.length);
  // "a/" 또는 "b/" 제거
  if (path.startsWith("a/")) {
    return path.slice(2);
  }
  if (path.startsWith("b/")) {
    return path.slice(2);
  }
  return path;
}

/**
 * hunk 파싱 (@@ -start,count +start,count @@)
 */
function parseHunk(lines: string[], startIndex: number): { hunk: PatchHunk; nextIndex: number } {
  const headerLine = lines[startIndex];
  const match = headerLine.match(/^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/);
  
  if (!match) {
    throw new Error(`Invalid hunk header at line ${startIndex + 1}: ${headerLine}`);
  }
  
  const oldStart = parseInt(match[1], 10);
  const oldLines = match[2] ? parseInt(match[2], 10) : 1;
  const newStart = parseInt(match[3], 10);
  const newLines = match[4] ? parseInt(match[4], 10) : 1;
  
  const hunkLines: HunkLine[] = [];
  let i = startIndex + 1;
  
  while (i < lines.length && !lines[i].startsWith("@@ ") && !lines[i].startsWith("--- ")) {
    const line = lines[i];
    
    if (line.startsWith("+")) {
      hunkLines.push({ type: "+", content: line.slice(1) });
    } else if (line.startsWith("-")) {
      hunkLines.push({ type: "-", content: line.slice(1) });
    } else if (line.startsWith("\\")) {
      hunkLines.push({ type: "\\", content: line.slice(1) });
    } else {
      // 공백 또는 컨텍스트 라인
      hunkLines.push({ type: " ", content: line.startsWith(" ") ? line.slice(1) : line });
    }
    
    i++;
  }
  
  return {
    hunk: {
      oldStart,
      oldLines,
      newStart,
      newLines,
      lines: hunkLines,
    },
    nextIndex: i,
  };
}

// ============================================================
// 보안 검증
// ============================================================

/**
 * 패치를 검증합니다.
 * 
 * 검증 항목:
 * 1. diff 형식 유효성
 * 2. 경로 탈출 시도 (../)
 * 3. 파일 확장자 allowlist
 * 4. 패치 크기 제한
 * 5. 파일 수 제한
 * 
 * @param patch unified diff 문자열
 * @param workspaceRoot 워크스페이스 루트 경로 (절대 경로)
 * @returns 검증 결과
 */
export function validatePatch(
  patch: string,
  workspaceRoot?: string
): PatchValidationResult {
  // 1. 빈 패치 검증
  if (!patch || patch.trim().length < 10) {
    return { valid: false, reason: "empty_or_too_small" };
  }
  
  // 2. 패치 크기 검증
  if (patch.length > MAX_PATCH_SIZE) {
    return { valid: false, reason: "patch_too_large" };
  }
  
  // 3. 경로 탈출 검증 (기본)
  if (patch.includes("../") || patch.includes("..\\")) {
    return { valid: false, reason: "path_traversal_suspected" };
  }
  
  // 4. diff 파싱 시도
  let parsedFiles: PatchFile[];
  try {
    parsedFiles = parseUnifiedDiff(patch);
  } catch (error) {
    return {
      valid: false,
      reason: "invalid_diff_format",
      files: [],
    };
  }
  
  // 5. 파일 수 제한
  if (parsedFiles.length > MAX_FILES) {
    return {
      valid: false,
      reason: "too_many_files",
      files: parsedFiles.map(f => f.newPath),
    };
  }
  
  // 6. 각 파일 검증
  const files: string[] = [];
  for (const file of parsedFiles) {
    // 경로 정규화 및 검증
    const normalizedOld = normalizePath(file.oldPath);
    const normalizedNew = normalizePath(file.newPath);
    
    if (!normalizedOld || !normalizedNew) {
      return {
        valid: false,
        reason: "invalid_path",
        files: [file.oldPath, file.newPath],
      };
    }
    
    // 워크스페이스 루트 검증 (제공된 경우)
    if (workspaceRoot) {
      if (!isWithinWorkspace(normalizedOld, workspaceRoot) ||
          !isWithinWorkspace(normalizedNew, workspaceRoot)) {
        return {
          valid: false,
          reason: "path_outside_workspace",
          files: [normalizedOld, normalizedNew],
        };
      }
    }
    
    // 확장자 검증
    const ext = getExtension(normalizedNew);
    if (ext && !ALLOWED_EXTENSIONS.has(ext)) {
      return {
        valid: false,
        reason: "extension_not_allowed",
        files: [normalizedNew],
      };
    }
    
    files.push(normalizedNew);
  }
  
  return {
    valid: true,
    files,
    parsedFiles,
  };
}

/**
 * 경로 정규화 및 검증
 */
function normalizePath(path: string): string | null {
  if (!path) return null;
  
  // 절대 경로 금지
  if (path.startsWith("/") || /^[A-Za-z]:/.test(path)) {
    return null;
  }
  
  // 경로 탈출 시도 차단
  if (path.includes("../") || path.includes("..\\")) {
    return null;
  }
  
  // 정규화 (중복 슬래시 제거 등)
  const normalized = path.replace(/\\/g, "/").replace(/\/+/g, "/");
  
  return normalized;
}

/**
 * 워크스페이스 내 경로인지 확인
 */
function isWithinWorkspace(filePath: string, workspaceRoot: string): boolean {
  const fullPath = filePath.startsWith("/")
    ? filePath
    : `${workspaceRoot}/${filePath}`;
  
  const resolved = path.resolve(fullPath);
  const rootResolved = path.resolve(workspaceRoot);
  
  return resolved.startsWith(rootResolved);
}

/**
 * 파일 확장자 추출
 */
function getExtension(path: string): string | null {
  const match = path.match(/\.[^.]+$/);
  return match ? match[0].toLowerCase() : null;
}

// ============================================================
// 패치 적용
// ============================================================

/**
 * 패치를 텍스트에 적용합니다.
 * 
 * @param original 원본 텍스트
 * @param patch unified diff 문자열
 * @returns 적용 결과
 */
export function applyPatchToText(
  original: string,
  patch: string
): ApplyPatchResult {
  const originalLines = original.split("\n");
  
  // 패치 파싱
  const parsedFiles = parseUnifiedDiff(patch);
  
  if (parsedFiles.length === 0) {
    return {
      success: false,
      content: original,
      appliedHunks: 0,
      conflicts: [{ file: "", hunkIndex: 0, reason: "no_files_in_patch" }],
    };
  }
  
  // 단일 파일 패치만 지원 (현재)
  const file = parsedFiles[0];
  const conflicts: ConflictInfo[] = [];
  let appliedHunks = 0;
  
  // 역순으로 적용 (라인 번호 변경 방지)
  const hunks = [...file.hunks].reverse();
  const resultLines = [...originalLines];
  
  for (let hunkIndex = 0; hunkIndex < hunks.length; hunkIndex++) {
    const hunk = hunks[hunkIndex];
    const startLine = hunk.oldStart - 1; // 0-based index
    
    // 범위 검증
    if (startLine < 0 || startLine >= resultLines.length) {
      conflicts.push({
        file: file.newPath,
        hunkIndex,
        reason: "invalid_line_range",
      });
      continue;
    }
    
    // 컨텍스트 매칭 확인
    const contextMatch = checkContextMatch(resultLines, hunk, startLine);
    if (!contextMatch.matched) {
      conflicts.push({
        file: file.newPath,
        hunkIndex,
        reason: contextMatch.reason || "context_mismatch",
      });
      continue;
    }
    
    // 패치 적용
    // 1. 기존 라인 제거
    const linesToRemove = hunk.oldLines;
    resultLines.splice(startLine, linesToRemove);
    
    // 2. 새 라인 삽입
    const newLines: string[] = [];
    for (const line of hunk.lines) {
      if (line.type === "+") {
        newLines.push(line.content);
      } else if (line.type === " ") {
        newLines.push(line.content);
      }
      // "-" 타입은 이미 제거됨
    }
    
    resultLines.splice(startLine, 0, ...newLines);
    appliedHunks++;
  }
  
  return {
    success: conflicts.length === 0,
    content: resultLines.join("\n"),
    appliedHunks,
    conflicts: conflicts.length > 0 ? conflicts : undefined,
  };
}

/**
 * 컨텍스트 매칭 확인
 */
function checkContextMatch(
  lines: string[],
  hunk: PatchHunk,
  startLine: number
): { matched: boolean; reason?: string } {
  // 컨텍스트 라인 확인
  let contextIndex = 0;
  for (const hunkLine of hunk.lines) {
    if (hunkLine.type === " ") {
      // 컨텍스트 라인은 일치해야 함
      const lineIndex = startLine + contextIndex;
      if (lineIndex >= lines.length) {
        return { matched: false, reason: "context_out_of_range" };
      }
      
      const expected = hunkLine.content;
      const actual = lines[lineIndex];
      
      if (actual !== expected) {
        return {
          matched: false,
          reason: `context_mismatch_at_line_${lineIndex + 1}`,
        };
      }
      
      contextIndex++;
    } else if (hunkLine.type === "-") {
      // 제거될 라인
      contextIndex++;
    }
    // "+" 타입은 새로 추가되므로 스킵
  }
  
  return { matched: true };
}

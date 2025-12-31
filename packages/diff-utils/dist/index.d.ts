/**
 * Diff Utils - Unified Diff 파서/검증/적용
 * Task C: Diff 유틸 구현
 *
 * 기능:
 * - unified diff 파싱
 * - 보안 검증 (경로 탈출, 확장자 allowlist, 크기 제한)
 * - 패치 적용
 */
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
/** 허용된 파일 확장자 (allowlist) */
export declare const ALLOWED_EXTENSIONS: Set<string>;
/** 최대 패치 크기 (바이트) */
export declare const MAX_PATCH_SIZE = 1000000;
/** 최대 파일 크기 (바이트) */
export declare const MAX_FILE_SIZE = 10000000;
/** 최대 파일 수 */
export declare const MAX_FILES = 100;
/**
 * unified diff 문자열을 파싱합니다.
 *
 * @param patch unified diff 문자열
 * @returns 파싱된 파일 목록
 */
export declare function parseUnifiedDiff(patch: string): PatchFile[];
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
export declare function validatePatch(patch: string, workspaceRoot?: string): PatchValidationResult;
/**
 * 패치를 텍스트에 적용합니다.
 *
 * @param original 원본 텍스트
 * @param patch unified diff 문자열
 * @returns 적용 결과
 */
export declare function applyPatchToText(original: string, patch: string): ApplyPatchResult;

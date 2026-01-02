/**
 * API 클라이언트 유틸리티
 * Web IDE에서 API 호출을 위한 클라이언트
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================
// Workspaces
// ============================================================

export interface Workspace {
  workspaceId: string;
  name: string;
  rootPath: string;
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces`);
  if (!response.ok) {
    throw new Error(`Failed to list workspaces: ${response.statusText}`);
  }
  return response.json();
}

export async function createWorkspace(name: string, language?: string): Promise<Workspace> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, language: language || "python" }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to create workspace: ${response.statusText}`);
  }
  return response.json();
}

export interface CloneGitHubRequest {
  repositoryUrl: string;
  name?: string;
  branch?: string;
}

export async function cloneGitHubRepository(
  request: CloneGitHubRequest
): Promise<Workspace> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(
      error.detail?.error || error.detail?.detail || `Failed to clone repository: ${response.statusText}`
    );
  }
  return response.json();
}

// ============================================================
// Files
// ============================================================

export interface FileTreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileTreeItem[];
}

export interface FileTree {
  workspaceId: string;
  tree: FileTreeItem[];
}

export async function getFileTree(workspaceId: string): Promise<FileTree> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces/${workspaceId}/files`);
  if (!response.ok) {
    throw new Error(`Failed to get file tree: ${response.statusText}`);
  }
  return response.json();
}

export interface FileContent {
  path: string;
  content: string;
  encoding: string;
}

export async function getFileContent(
  workspaceId: string,
  path: string
): Promise<FileContent> {
  const response = await fetch(
    `${API_BASE_URL}/api/workspaces/${workspaceId}/files/content?path=${encodeURIComponent(path)}`
  );
  if (!response.ok) {
    throw new Error(`Failed to get file content: ${response.statusText}`);
  }
  return response.json();
}

export async function updateFileContent(
  workspaceId: string,
  path: string,
  content: string
): Promise<{ path: string; success: boolean; message?: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/workspaces/${workspaceId}/files/content`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    }
  );
  if (!response.ok) {
    throw new Error(`Failed to update file: ${response.statusText}`);
  }
  return response.json();
}

/**
 * 새 파일 생성 (빈 파일 또는 초기 내용 포함)
 */
export async function createFile(
  workspaceId: string,
  path: string,
  content: string = ""
): Promise<{ path: string; success: boolean; message?: string }> {
  // PUT /files/content를 사용하여 파일 생성
  return updateFileContent(workspaceId, path, content);
}

// ============================================================
// AI
// ============================================================

export interface AIExplainRequest {
  workspaceId: string;
  filePath: string;
  selection?: { startLine: number; endLine: number };
}

export interface AIExplainResponse {
  explanation: string;
  tokensUsed?: number;
}

export async function explainCode(request: AIExplainRequest): Promise<AIExplainResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to explain code: ${response.statusText}`);
  }
  return response.json();
}

export interface AIRewriteRequest {
  workspaceId: string;
  instruction: string;
  target: {
    file: string;
    selection: { startLine: number; endLine: number };
  };
}

export interface AIRewriteResponse {
  diff: string;
  tokensUsed?: number;
}

export async function rewriteCode(request: AIRewriteRequest): Promise<AIRewriteResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/rewrite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to rewrite code: ${response.statusText}`);
  }
  return response.json();
}

// ============================================================
// Patch
// ============================================================

export interface PatchValidateRequest {
  workspaceId: string;
  patch: string;
}

export interface PatchValidateResponse {
  valid: boolean;
  reason?: string;
  files?: string[];
}

export async function validatePatch(
  request: PatchValidateRequest
): Promise<PatchValidateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patch/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Failed to validate patch: ${response.statusText}`);
  }
  return response.json();
}

export interface PatchApplyRequest {
  workspaceId: string;
  patch: string;
  dryRun?: boolean;
}

export interface PatchApplyResponse {
  success: boolean;
  appliedFiles: string[];
  message?: string;
}

export async function applyPatch(request: PatchApplyRequest): Promise<PatchApplyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patch/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.error || `Failed to apply patch: ${response.statusText}`);
  }
  return response.json();
}

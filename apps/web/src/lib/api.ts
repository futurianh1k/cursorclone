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

// AI Chat - 대화형 인터페이스
export interface AIChatRequest {
  workspaceId: string;
  message: string;
  filePath?: string;
  fileContent?: string;
  selection?: { startLine: number; endLine: number };
  history?: Array<{ role: "user" | "assistant"; content: string }>;
}

export interface AIChatResponse {
  response: string;
  tokensUsed?: number;
  suggestedAction?: string;
}

export async function chatWithAI(request: AIChatRequest): Promise<AIChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to chat with AI: ${response.statusText}`);
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
// AI Modes: Plan, Agent, Debug
// ============================================================

// --- Plan Mode ---
export interface TaskStep {
  stepNumber: number;
  description: string;
  status: string;
  filePath?: string;
}

export interface AIPlanRequest {
  workspaceId: string;
  goal: string;
  context?: string;
  filePaths?: string[];
}

export interface AIPlanResponse {
  summary: string;
  steps: TaskStep[];
  estimatedChanges: number;
  tokensUsed: number;
}

export async function createPlan(request: AIPlanRequest): Promise<AIPlanResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to create plan: ${response.statusText}`);
  }
  return response.json();
}

// --- Agent Mode ---
export interface FileChange {
  filePath: string;
  action: "create" | "modify" | "delete";
  diff?: string;
  description: string;
}

export interface AIAgentRequest {
  workspaceId: string;
  instruction: string;
  filePaths?: string[];
  autoApply?: boolean;
}

export interface AIAgentResponse {
  summary: string;
  changes: FileChange[];
  applied: boolean;
  tokensUsed: number;
}

export async function runAgent(request: AIAgentRequest): Promise<AIAgentResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to run agent: ${response.statusText}`);
  }
  return response.json();
}

// --- Debug Mode ---
export interface BugFix {
  filePath: string;
  lineNumber?: number;
  originalCode: string;
  fixedCode: string;
  explanation: string;
}

export interface AIDebugRequest {
  workspaceId: string;
  errorMessage?: string;
  stackTrace?: string;
  filePath?: string;
  fileContent?: string;
  description?: string;
}

export interface AIDebugResponse {
  diagnosis: string;
  rootCause: string;
  fixes: BugFix[];
  preventionTips?: string[];
  tokensUsed: number;
}

export async function debugCode(request: AIDebugRequest): Promise<AIDebugResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/debug`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to debug: ${response.statusText}`);
  }
  return response.json();
}

// --- Get Available Modes ---
export interface AIMode {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface AIModesResponse {
  modes: AIMode[];
  current: string;
}

export async function getAIModes(): Promise<AIModesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/modes`);
  if (!response.ok) {
    throw new Error(`Failed to get AI modes: ${response.statusText}`);
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

// ============================================================
// SSH
// ============================================================

export interface SSHConnectionInfo {
  host: string;
  port: number;
  username: string;
  authType: string;
}

export interface SSHConnectionResponse {
  workspaceId: string;
  connection: SSHConnectionInfo;
  status: "available" | "unavailable";
  sshCommand: string;
  vscodeRemoteUri: string;
}

export interface SSHKeyResponse {
  success: boolean;
  message: string;
  workspaceId: string;
  fingerprint?: string;
}

export interface GenerateSSHKeyResponse {
  success: boolean;
  message: string;
  publicKey: string;
  privateKey: string;
  fingerprint: string;
}

export interface CursorSSHCommandResponse {
  workspaceId: string;
  instructions: {
    step1: string;
    step2: string;
    step3: string;
  };
  sshConfig: {
    description: string;
    content: string;
  };
  vscodeRemoteUri: string;
  directCommand: string;
}

export async function getSSHConnectionInfo(workspaceId: string): Promise<SSHConnectionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces/${workspaceId}/ssh/info`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to get SSH info: ${response.statusText}`);
  }
  return response.json();
}

export async function setupSSHKey(workspaceId: string, publicKey: string): Promise<SSHKeyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces/${workspaceId}/ssh/key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ publicKey }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to setup SSH key: ${response.statusText}`);
  }
  return response.json();
}

export async function setupSSHPassword(workspaceId: string, password: string): Promise<SSHKeyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces/${workspaceId}/ssh/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to setup SSH password: ${response.statusText}`);
  }
  return response.json();
}

export async function generateSSHKeyPair(workspaceId: string, keyType: "rsa" | "ed25519" = "ed25519"): Promise<GenerateSSHKeyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces/${workspaceId}/ssh/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key_type: keyType }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to generate SSH key: ${response.statusText}`);
  }
  return response.json();
}

export async function getCursorSSHCommand(workspaceId: string): Promise<CursorSSHCommandResponse> {
  const response = await fetch(`${API_BASE_URL}/api/workspaces/${workspaceId}/ssh/cursor-command`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to get Cursor SSH command: ${response.statusText}`);
  }
  return response.json();
}

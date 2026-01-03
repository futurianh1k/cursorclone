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
// 파일 업로드/다운로드
// ============================================================

export interface UploadResult {
  success: boolean;
  uploadedFiles: Array<{ path: string; size: number }>;
  errors: Array<{ file: string; error: string }>;
  totalUploaded: number;
  totalErrors: number;
}

export interface ZipUploadResult {
  success: boolean;
  extractedFiles: Array<{ path: string; size: number }>;
  errors: Array<{ file: string; error: string }>;
  totalExtracted: number;
  totalErrors: number;
}

/**
 * 파일 업로드 (단일 또는 다중)
 */
export async function uploadFiles(
  workspaceId: string,
  files: File[],
  targetDir: string = "",
  overwrite: boolean = false
): Promise<UploadResult> {
  const formData = new FormData();
  
  files.forEach((file) => {
    formData.append("files", file);
  });
  
  formData.append("target_dir", targetDir);
  formData.append("overwrite", String(overwrite));
  
  const response = await fetch(
    `${API_BASE_URL}/api/workspaces/${workspaceId}/files/upload`,
    {
      method: "POST",
      body: formData,
    }
  );
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to upload files: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * ZIP 파일 업로드 및 압축 해제
 */
export async function uploadZip(
  workspaceId: string,
  file: File,
  targetDir: string = "",
  overwrite: boolean = false
): Promise<ZipUploadResult> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("target_dir", targetDir);
  formData.append("overwrite", String(overwrite));
  
  const response = await fetch(
    `${API_BASE_URL}/api/workspaces/${workspaceId}/files/upload/zip`,
    {
      method: "POST",
      body: formData,
    }
  );
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to upload ZIP: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * 파일 다운로드
 */
export async function downloadFile(workspaceId: string, path: string): Promise<Blob> {
  const response = await fetch(
    `${API_BASE_URL}/api/workspaces/${workspaceId}/files/download?path=${encodeURIComponent(path)}`
  );
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to download file: ${response.statusText}`);
  }
  
  return response.blob();
}

/**
 * 파일/폴더 삭제
 */
export async function deleteFile(
  workspaceId: string,
  path: string,
  recursive: boolean = false
): Promise<{ success: boolean; path: string; message: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/workspaces/${workspaceId}/files?path=${encodeURIComponent(path)}&recursive=${recursive}`,
    { method: "DELETE" }
  );
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to delete file: ${response.statusText}`);
  }
  
  return response.json();
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
// AIMode: 문자열 리터럴 타입 (agent, ask, plan, debug)
export type AIModeType = "agent" | "ask" | "plan" | "debug";

// AIModeInfo: 모드 정보 객체 (UI 표시용)
export interface AIModeInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface AIModesResponse {
  modes: AIModeInfo[];
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

// ============================================================
// AI Advanced Chat (Cursor-like features)
// ============================================================

export type ContextType = "file" | "selection" | "folder" | "image" | "url" | "clipboard";

export interface ContextItem {
  type: ContextType;
  path?: string;
  content?: string;
  selection?: { startLine: number; endLine: number };
  imageUrl?: string;
  imageBase64?: string;
  mimeType?: string;
  name?: string;
}

export interface AIAdvancedChatRequest {
  workspaceId: string;
  message: string;
  mode: AIModeType;
  contexts?: ContextItem[];
  history?: Array<{ role: string; content: string }>;
  currentFile?: string;
  currentContent?: string;
  currentSelection?: { startLine: number; endLine: number };
}

export interface AIAdvancedChatResponse {
  response: string;
  mode: AIModeType;
  tokensUsed: number;
  planSteps?: TaskStep[];
  fileChanges?: FileChange[];
  bugFixes?: Array<{
    filePath: string;
    lineNumber?: number;
    originalCode: string;
    fixedCode: string;
    explanation: string;
  }>;
  suggestedAction?: string;
}

export async function advancedChatWithAI(request: AIAdvancedChatRequest): Promise<AIAdvancedChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/advanced/chat`, {
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

// ============================================================
// Image Upload & Analysis
// ============================================================

export interface ImageUploadResponse {
  imageId: string;
  imageUrl: string;
  thumbnailUrl?: string;
  mimeType: string;
  size: number;
  width?: number;
  height?: number;
}

export async function uploadImage(file: File): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${API_BASE_URL}/api/ai/image/upload`, {
    method: "POST",
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to upload image: ${response.statusText}`);
  }
  
  return response.json();
}

export interface ImageAnalysisRequest {
  workspaceId: string;
  imageUrl?: string;
  imageBase64?: string;
  question?: string;
}

export interface ImageAnalysisResponse {
  description: string;
  extractedText?: string;
  codeBlocks?: string[];
}

export async function analyzeImage(request: ImageAnalysisRequest): Promise<ImageAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/image/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to analyze image: ${response.statusText}`);
  }
  
  return response.json();
}

// ============================================================
// Context Suggestion (@ autocomplete)
// ============================================================

export interface ContextSuggestion {
  type: ContextType;
  path?: string;
  name: string;
  preview?: string;
  relevance: number;
}

export interface ContextSuggestResponse {
  suggestions: ContextSuggestion[];
  total: number;
}

export async function suggestContext(
  workspaceId: string,
  query: string,
  types?: ContextType[],
  limit: number = 10
): Promise<ContextSuggestResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ai/context/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      workspaceId,
      query,
      types,
      limit,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to get suggestions: ${response.statusText}`);
  }
  
  return response.json();
}

// ============================================================
// IDE Container (code-server) API
// ============================================================

export type IDEContainerStatus = "pending" | "starting" | "running" | "stopping" | "stopped" | "error";
export type IDEType = "code-server" | "jupyter" | "theia";

export interface IDEContainerConfig {
  cpuLimit?: string;
  memoryLimit?: string;
  storageSize?: string;
  gpuEnabled?: boolean;
  extensions?: string[];
  environment?: Record<string, string>;
}

export interface CreateIDEContainerRequest {
  workspaceId: string;
  ideType?: IDEType;
  config?: IDEContainerConfig;
}

export interface IDEContainerResponse {
  containerId: string;
  workspaceId: string;
  userId: string;
  ideType: IDEType;
  status: IDEContainerStatus;
  url?: string;
  internalUrl?: string;
  port?: number;
  createdAt: string;
  lastAccessed?: string;
  config?: IDEContainerConfig;
}

export interface IDEContainerListResponse {
  containers: IDEContainerResponse[];
  total: number;
}

export interface StartIDEContainerResponse {
  containerId: string;
  status: IDEContainerStatus;
  url: string;
  token?: string;
  expiresAt?: string;
}

export interface StopIDEContainerResponse {
  containerId: string;
  status: IDEContainerStatus;
  message: string;
}

export interface IDEHealthResponse {
  totalContainers: number;
  runningContainers: number;
  availableCapacity: number;
  avgCpuUsage: number;
  avgMemoryUsage: number;
}

/**
 * IDE 컨테이너 생성
 */
export async function createIDEContainer(request: CreateIDEContainerRequest): Promise<IDEContainerResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ide/containers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to create IDE container: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * IDE 컨테이너 목록 조회
 */
export async function listIDEContainers(workspaceId?: string): Promise<IDEContainerListResponse> {
  const params = new URLSearchParams();
  if (workspaceId) params.append("workspace_id", workspaceId);
  
  const response = await fetch(`${API_BASE_URL}/api/ide/containers?${params.toString()}`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to list IDE containers: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * IDE 컨테이너 상세 조회
 */
export async function getIDEContainer(containerId: string): Promise<IDEContainerResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ide/containers/${containerId}`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to get IDE container: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * IDE 컨테이너 시작
 */
export async function startIDEContainer(containerId: string): Promise<StartIDEContainerResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ide/containers/${containerId}/start`, {
    method: "POST",
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to start IDE container: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * IDE 컨테이너 중지
 */
export async function stopIDEContainer(containerId: string): Promise<StopIDEContainerResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ide/containers/${containerId}/stop`, {
    method: "POST",
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to stop IDE container: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * IDE 컨테이너 삭제
 */
export async function deleteIDEContainer(containerId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE_URL}/api/ide/containers/${containerId}`, {
    method: "DELETE",
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to delete IDE container: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * 워크스페이스의 IDE URL 조회 (또는 생성)
 * PoC에서는 공유 code-server 인스턴스 URL 반환
 */
export async function getWorkspaceIDEUrl(workspaceId: string): Promise<{
  url: string;
  containerId: string | null;
  status: "existing" | "shared" | "created";
}> {
  const response = await fetch(`${API_BASE_URL}/api/ide/workspace/${workspaceId}/url`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to get IDE URL: ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * IDE 서비스 상태 조회
 */
export async function getIDEHealth(): Promise<IDEHealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ide/health`);
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail || `Failed to get IDE health: ${response.statusText}`);
  }
  
  return response.json();
}

export type WorkspaceId = string;

export interface CreateWorkspaceRequest {
  name: string;
  language: string;
}

export interface CreateWorkspaceResponse {
  workspaceId: WorkspaceId;
  rootPath: string;
}

export interface RewriteSelectionRequest {
  workspaceId: WorkspaceId;
  instruction: string;
  target: {
    file: string;
    selection: { startLine: number; endLine: number };
  };
}

export interface PatchValidateRequest {
  workspaceId: WorkspaceId;
  patch: string;
}

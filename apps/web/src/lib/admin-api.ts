/**
 * 관리자 API 클라이언트
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Server {
  serverId: string;
  name: string;
  host: string;
  port: number;
  type: "kubernetes" | "docker" | "ssh";
  region?: string;
  zone?: string;
  status: "active" | "inactive" | "maintenance";
  maxWorkspaces: number;
  currentWorkspaces: number;
  cpuCapacity?: number;
  memoryCapacity?: number;
  diskCapacity?: number;
  cpuUsage?: number;
  memoryUsage?: number;
  diskUsage?: number;
  lastHealthCheck?: string;
}

export interface RegisterServerRequest {
  name: string;
  host: string;
  port?: number;
  type: "kubernetes" | "docker" | "ssh";
  region?: string;
  zone?: string;
  maxWorkspaces?: number;
  auth: {
    type: "ssh_key" | "mtls" | "api_key";
    private_key?: string;
    public_key?: string;
    certificate?: string;
    api_key?: string;
  };
}

export async function listServers(): Promise<Server[]> {
  const response = await fetch(`${API_BASE_URL}/api/admin/servers`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Failed to list servers: ${response.statusText}`);
  }
  return response.json();
}

export async function registerServer(request: RegisterServerRequest): Promise<Server> {
  const response = await fetch(`${API_BASE_URL}/api/admin/servers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to register server: ${response.statusText}`);
  }
  return response.json();
}

/** 서버 리소스 정보 */
export interface ServerResourceInfo {
  cpuCores?: number;
  memoryTotal?: number;
  memoryAvailable?: number;
  diskTotal?: number;
  diskAvailable?: number;
  kubernetesVersion?: string;
  nodeCount?: number;
}

export async function testServerConnection(serverId: string): Promise<{
  success: boolean;
  message: string;
  resourceInfo?: ServerResourceInfo;
}> {
  const response = await fetch(`${API_BASE_URL}/api/admin/servers/${serverId}/test`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to test connection: ${response.statusText}`);
  }
  return response.json();
}

export async function placeWorkspace(
  workspaceId: string,
  request: {
    serverId?: string;
    policy?: "round_robin" | "least_loaded" | "region_based";
    region?: string;
  }
): Promise<{
  workspaceId: string;
  serverId: string;
  serverName: string;
  placementId?: string;
}> {
  const response = await fetch(`${API_BASE_URL}/api/admin/workspaces/${workspaceId}/place`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(error.detail?.error || `Failed to place workspace: ${response.statusText}`);
  }
  return response.json();
}

import fs from "node:fs";

export type E2EState = {
  apiUrl: string;
  webUrl: string;
  gatewayUrl: string;
  accessToken: string;
  gatewayToken: string;
  projectId: string;
  workspaceId: string;
};

export function loadCreds(): { email: string; password: string } {
  const p = process.env.E2E_CREDS_PATH;
  if (!p) throw new Error("E2E_CREDS_PATH not set (globalSetup failed?)");
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

export function loadState(): E2EState {
  const p = process.env.E2E_STATE_PATH;
  if (!p) throw new Error("E2E_STATE_PATH not set (globalSetup failed?)");
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}


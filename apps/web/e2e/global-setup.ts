import { chromium, FullConfig } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

type Creds = { email: string; password: string };

function rnd(): string {
  return Math.random().toString(16).slice(2, 10);
}

async function apiSignupAndLogin(apiUrl: string, email: string, password: string): Promise<string> {
  // signup
  await fetch(`${apiUrl}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      name: "Playwright E2E",
      password,
      org_name: "org_default",
    }),
  }).catch(() => null);

  // login
  const r = await fetch(`${apiUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const txt = await r.text().catch(() => "");
    throw new Error(`E2E login failed: ${r.status} ${txt}`);
  }
  const data = (await r.json()) as { accessToken: string };
  if (!data.accessToken) throw new Error("E2E login response missing accessToken");
  return data.accessToken;
}

export default async function globalSetup(config: FullConfig) {
  const webUrl = process.env.E2E_WEB_URL || process.env.WEB_URL || "http://localhost:3000";
  const apiUrl = process.env.E2E_API_URL || process.env.API_URL || "http://localhost:8000";

  const outDir = path.join(process.cwd(), ".e2e");
  fs.mkdirSync(outDir, { recursive: true });
  const storageStatePath = path.join(outDir, "storage-state.json");
  const credsPath = path.join(outDir, "creds.json");

  const password = process.env.E2E_PASSWORD || "ChangeMe1234!";
  const email = process.env.E2E_EMAIL || `pw-e2e-${Date.now()}-${rnd()}@example.com`;

  const token = await apiSignupAndLogin(apiUrl, email, password);

  // Create storageState with localStorage access_token
  const browser = await chromium.launch({
    executablePath:
      process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ||
      process.env.CHROMIUM_PATH ||
      process.env.CHROME_PATH ||
      "/usr/bin/chromium",
  });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(webUrl, { waitUntil: "domcontentloaded" });
  await page.addInitScript((t) => {
    localStorage.setItem("access_token", t);
  }, token);
  // Reload to ensure initScript applied to an actual document
  await page.reload({ waitUntil: "domcontentloaded" });
  await context.storageState({ path: storageStatePath });
  await browser.close();

  fs.writeFileSync(credsPath, JSON.stringify({ email, password } satisfies Creds, null, 2) + "\n", "utf-8");

  // Expose paths to tests
  process.env.E2E_STORAGE_STATE = storageStatePath;
  process.env.E2E_CREDS_PATH = credsPath;
}


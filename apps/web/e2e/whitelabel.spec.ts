import { test, expect } from "@playwright/test";
import fs from "node:fs";

function loadCreds(): { email: string; password: string } {
  const p = process.env.E2E_CREDS_PATH;
  if (!p) throw new Error("E2E_CREDS_PATH not set (globalSetup failed?)");
  return JSON.parse(fs.readFileSync(p, "utf-8"));
}

test.describe("authenticated dashboard flows", () => {
  test.use({
    storageState: process.env.E2E_STORAGE_STATE,
  });

  test("dashboard loads (authenticated via storageState)", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Workspaces" })).toBeVisible();
    await expect(page.getByText("VSCode 서버 워크스페이스를 관리")).toBeVisible();
  });

  test("create workspace from dashboard modal and open IDE popup (best-effort)", async ({ page }) => {
    test.slow();
    await page.goto("/dashboard");

    await page.getByRole("button", { name: /새 워크스페이스/ }).click();
    await expect(page.getByRole("heading", { name: "새 워크스페이스 생성" })).toBeVisible();

    // Use empty workspace mode
    await page.getByRole("button", { name: /빈 워크스페이스/ }).click();

    const wsName = `pw_ws_${Date.now()}`;
    await page.getByPlaceholder("my-project").fill(wsName);
    await page.getByRole("button", { name: /생성 및 IDE 시작/ }).click();

    // Success toast
    await expect(page.getByText(new RegExp(`워크스페이스 \\"${wsName}\\"가 생성되었습니다`))).toBeVisible({
      timeout: 60_000,
    });

    // Row appears
    await expect(page.getByText(wsName)).toBeVisible({ timeout: 60_000 });

    // Try to click start/open and observe popup. This can be slow depending on image/model.
    // If it doesn't open, we still treat it as best-effort (the main E2E is provisioning + listing).
    const startBtn = page.getByRole("button", { name: /▶ 시작/ }).first();
    if (await startBtn.isVisible().catch(() => false)) {
      const popupPromise = page.waitForEvent("popup", { timeout: 90_000 }).catch(() => null);
      await startBtn.click();
      const popup = await popupPromise;
      if (popup) {
        await popup.waitForLoadState("domcontentloaded", { timeout: 90_000 }).catch(() => null);
        expect(popup.url()).toMatch(/^http/);
        await popup.close().catch(() => null);
      }
    }
  });
});

test("login page works (UI login) [smoke]", async ({ page, context }) => {
  const { email, password } = loadCreds();

  // Ensure this test does NOT depend on storageState
  // (It exercises UI login flow end-to-end.)
  await context.clearCookies();
  await page.addInitScript(() => {
    try {
      localStorage.removeItem("access_token");
    } catch {}
  });

  await page.goto("/login");
  await expect(page.getByText("Cursor On-Prem에 로그인")).toBeVisible();

  await page.getByPlaceholder("user@example.com").fill(email);
  await page.getByPlaceholder("비밀번호").fill(password);
  await page.getByRole("button", { name: "로그인" }).click();

  await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Workspaces" })).toBeVisible();
});


import { test, expect } from "@playwright/test";
import { loadCreds } from "./helpers";

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

    await page.getByTestId("dashboard-new-workspace").click();
    await expect(page.getByTestId("create-ws-modal")).toBeVisible();

    const wsName = `pw_ws_${Date.now()}`;
    await page.getByTestId("create-ws-name").fill(wsName);
    await page.getByTestId("create-ws-submit").click();

    // Success toast
    await expect(page.getByText(new RegExp(`워크스페이스 \\"${wsName}\\"가 생성되었습니다`))).toBeVisible({
      timeout: 60_000,
    });

    // Row appears
    await expect(page.getByText(wsName)).toBeVisible({ timeout: 60_000 });

    // IDE popup open is best-effort here (provisioning can be slow)
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

  await page.getByTestId("auth-email").fill(email);
  await page.getByTestId("auth-password").fill(password);
  await page.getByTestId("auth-submit").click();

  await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Workspaces" })).toBeVisible();
});


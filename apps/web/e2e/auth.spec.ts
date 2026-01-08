import { test, expect } from "@playwright/test";
import { loadCreds } from "./helpers";

test("unauthenticated access to /dashboard redirects to /login", async ({ page }) => {
  await page.addInitScript(() => {
    try {
      localStorage.removeItem("access_token");
    } catch {}
  });
  await page.goto("/dashboard");
  await page.waitForURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByText("Cursor On-Prem에 로그인")).toBeVisible();
});

test("logout clears session and returns to /login", async ({ page }) => {
  // Login via UI (fresh)
  const { email, password } = loadCreds();
  await page.addInitScript(() => {
    try {
      localStorage.removeItem("access_token");
    } catch {}
  });
  await page.goto("/login");
  await page.getByTestId("auth-email").fill(email);
  await page.getByTestId("auth-password").fill(password);
  await page.getByTestId("auth-submit").click();

  await page.waitForURL(/\/dashboard/, { timeout: 30_000 });
  await expect(page.getByRole("heading", { name: "Workspaces" })).toBeVisible();

  await page.getByTestId("dashboard-logout").click();
  await page.waitForURL(/\/login/, { timeout: 15_000 });
  await expect(page.getByText("Cursor On-Prem에 로그인")).toBeVisible();
});

import { test, expect } from '@playwright/test';

/**
 * 인증 E2E 테스트
 */
test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // 로그인 페이지로 이동
    await page.goto('/login');
  });

  test('로그인 페이지가 표시된다', async ({ page }) => {
    // 제목 확인
    await expect(page.getByRole('heading', { name: '로그인' })).toBeVisible();
    
    // 입력 필드 확인
    await expect(page.getByLabel('이메일')).toBeVisible();
    await expect(page.getByLabel('비밀번호')).toBeVisible();
    
    // 로그인 버튼 확인
    await expect(page.getByRole('button', { name: '로그인' })).toBeVisible();
  });

  test('빈 폼 제출 시 검증 에러', async ({ page }) => {
    // 폼 제출
    await page.getByRole('button', { name: '로그인' }).click();
    
    // HTML5 검증 에러 (required 필드)
    // 이메일 필드가 invalid 상태인지 확인
    const emailInput = page.getByLabel('이메일');
    await expect(emailInput).toHaveAttribute('required');
  });

  test('회원가입 모드로 전환', async ({ page }) => {
    // 회원가입 링크 클릭
    await page.getByRole('button', { name: '회원가입' }).click();
    
    // 회원가입 폼 확인
    await expect(page.getByLabel('이름')).toBeVisible();
    await expect(page.getByPlaceholder('홍길동')).toBeVisible();
  });

  test('로그인 성공 시 대시보드로 이동', async ({ page }) => {
    // Mock API 응답 설정
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          accessToken: 'mock-token',
          tokenType: 'bearer',
          user: {
            userId: 'u-123',
            email: 'test@example.com',
            name: 'Test User',
            orgId: 'org-123',
            role: 'developer',
          },
        }),
      });
    });

    // 로그인 정보 입력
    await page.getByLabel('이메일').fill('test@example.com');
    await page.getByLabel('비밀번호').fill('password123');
    
    // 로그인 버튼 클릭
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 대시보드로 이동 확인
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('잘못된 자격 증명으로 에러 표시', async ({ page }) => {
    // Mock API 응답 설정 (401 에러)
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            error: 'Invalid email or password',
            code: 'INVALID_CREDENTIALS',
          },
        }),
      });
    });

    // 로그인 정보 입력
    await page.getByLabel('이메일').fill('wrong@example.com');
    await page.getByLabel('비밀번호').fill('wrongpassword');
    
    // 로그인 버튼 클릭
    await page.getByRole('button', { name: '로그인' }).click();
    
    // 에러 메시지 확인
    await expect(page.getByText(/Invalid email or password|로그인에 실패/)).toBeVisible();
  });
});

test.describe('Authentication - Accessibility', () => {
  test('키보드로 로그인 가능', async ({ page }) => {
    await page.goto('/login');
    
    // Tab으로 이메일 필드로 이동
    await page.keyboard.press('Tab');
    await page.keyboard.type('test@example.com');
    
    // Tab으로 비밀번호 필드로 이동
    await page.keyboard.press('Tab');
    await page.keyboard.type('password123');
    
    // Tab으로 로그인 버튼으로 이동
    await page.keyboard.press('Tab');
    
    // Enter로 제출
    // (실제 API 호출 전에 확인만)
    const submitButton = page.getByRole('button', { name: '로그인' });
    await expect(submitButton).toBeFocused();
  });

  test('스킵 네비게이션 링크 동작', async ({ page }) => {
    await page.goto('/login');
    
    // 스킵 링크 확인 (Tab 누르면 나타남)
    await page.keyboard.press('Tab');
    
    const skipLink = page.getByRole('link', { name: '메인 콘텐츠로 건너뛰기' });
    // 스킵 링크가 포커스를 받으면 보임
    await expect(skipLink).toBeFocused();
  });
});

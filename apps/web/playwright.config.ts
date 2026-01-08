import { defineConfig, devices } from "@playwright/test";

const webUrl = process.env.E2E_WEB_URL || process.env.WEB_URL || "http://localhost:3000";

// On-prem / restricted network:
// - Do NOT auto-download Playwright browsers.
// - Use system chromium or set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH.
const chromiumExecutable =
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ||
  process.env.CHROMIUM_PATH ||
  process.env.CHROME_PATH ||
  "/usr/bin/chromium";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: webUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          executablePath: chromiumExecutable,
        },
      },
    },
  ],
  globalSetup: require.resolve("./e2e/global-setup"),
  outputDir: "test-results",
});

import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E 테스트 설정
 * 
 * 실행 방법:
 *   npx playwright test              - 전체 테스트
 *   npx playwright test --ui         - UI 모드
 *   npx playwright test --headed     - 브라우저 표시
 */
export default defineConfig({
  // 테스트 디렉토리
  testDir: './e2e',
  
  // 테스트 타임아웃
  timeout: 30 * 1000,
  
  // 전체 실행 타임아웃
  globalTimeout: 10 * 60 * 1000,
  
  // 재시도 횟수
  retries: process.env.CI ? 2 : 0,
  
  // 병렬 실행 워커 수
  workers: process.env.CI ? 1 : undefined,
  
  // 리포터
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
    ...(process.env.CI ? [['github'] as const] : []),
  ],
  
  // 공통 설정
  use: {
    // 기본 URL
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    
    // 스크린샷 (실패 시)
    screenshot: 'only-on-failure',
    
    // 비디오 (실패 시)
    video: 'on-first-retry',
    
    // 트레이스 (실패 시)
    trace: 'on-first-retry',
    
    // 액션 타임아웃
    actionTimeout: 10 * 1000,
  },
  
  // 브라우저 프로젝트
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 모바일 뷰포트
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  
  // 웹서버 자동 시작 (로컬)
  webServer: process.env.CI ? undefined : {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60 * 1000,
  },
});

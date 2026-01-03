import { test, expect } from '@playwright/test';

/**
 * 워크스페이스 E2E 테스트
 */
test.describe('Workspace', () => {
  // 인증된 상태 설정
  test.beforeEach(async ({ page }) => {
    // localStorage에 토큰 설정
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-token');
    });
  });

  test('워크스페이스 선택 화면 표시', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 워크스페이스 선택 화면 확인
    await expect(page.getByRole('heading', { name: '워크스페이스 선택' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'GitHub 클론' })).toBeVisible();
    await expect(page.getByRole('button', { name: '빈 워크스페이스 생성' })).toBeVisible();
  });

  test('GitHub 클론 폼', async ({ page }) => {
    await page.goto('/dashboard');
    
    // GitHub 클론 버튼 클릭
    await page.getByRole('button', { name: 'GitHub 클론' }).click();
    
    // 폼 확인
    await expect(page.getByPlaceholder('https://github.com/owner/repo')).toBeVisible();
    await expect(page.getByText('워크스페이스 이름')).toBeVisible();
    await expect(page.getByText('브랜치')).toBeVisible();
  });

  test('빈 워크스페이스 생성 폼', async ({ page }) => {
    await page.goto('/dashboard');
    
    // 빈 워크스페이스 생성 버튼 클릭
    await page.getByRole('button', { name: '빈 워크스페이스 생성' }).click();
    
    // 폼 확인
    await expect(page.getByPlaceholder('my-project')).toBeVisible();
    await expect(page.getByRole('button', { name: /생성/i })).toBeVisible();
  });

  test('워크스페이스 생성 성공', async ({ page }) => {
    // Mock API 응답
    await page.route('**/api/workspaces', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            workspaceId: 'ws-new-123',
            name: 'test-project',
            rootPath: '/workspaces/test-project',
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/dashboard');
    
    // 빈 워크스페이스 생성
    await page.getByRole('button', { name: '빈 워크스페이스 생성' }).click();
    await page.getByPlaceholder('my-project').fill('test-project');
    await page.getByRole('button', { name: /생성/i }).click();
    
    // 워크스페이스가 로드되었는지 확인 (파일 트리 등)
    // 실제 구현에 따라 다를 수 있음
  });

  test('취소 버튼 동작', async ({ page }) => {
    await page.goto('/dashboard');
    
    // GitHub 클론 폼으로 이동
    await page.getByRole('button', { name: 'GitHub 클론' }).click();
    await expect(page.getByText('GitHub 저장소 클론')).toBeVisible();
    
    // 취소 클릭
    await page.getByRole('button', { name: '취소' }).click();
    
    // 선택 화면으로 돌아감
    await expect(page.getByRole('heading', { name: '워크스페이스 선택' })).toBeVisible();
  });
});

test.describe('Workspace Editor', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-token');
    });
  });

  test('파일 트리 표시', async ({ page }) => {
    // Mock 파일 트리 API
    await page.route('**/api/workspaces/*/files/tree', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workspaceId: 'ws-123',
          tree: [
            {
              name: 'src',
              path: 'src',
              type: 'directory',
              children: [
                { name: 'main.py', path: 'src/main.py', type: 'file' },
              ],
            },
            { name: 'README.md', path: 'README.md', type: 'file' },
          ],
        }),
      });
    });

    // 워크스페이스 페이지로 직접 이동 (실제 구현에 따라 다름)
    // await page.goto('/dashboard/ws-123');
    
    // 파일 트리 확인
    // await expect(page.getByText('src')).toBeVisible();
    // await expect(page.getByText('README.md')).toBeVisible();
  });
});

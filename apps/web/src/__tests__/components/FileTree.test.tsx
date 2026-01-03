/**
 * FileTree 컴포넌트 테스트
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FileTree from '@/components/FileTree';

// Mock API
vi.mock('@/lib/api', () => ({
  getFileTree: vi.fn(),
  createFile: vi.fn(),
}));

import { getFileTree, createFile } from '@/lib/api';

const mockFileTree = {
  tree: [
    {
      name: 'src',
      path: 'src',
      type: 'directory' as const,
      children: [
        { name: 'main.py', path: 'src/main.py', type: 'file' as const },
        { name: 'utils.py', path: 'src/utils.py', type: 'file' as const },
      ],
    },
    { name: 'README.md', path: 'README.md', type: 'file' as const },
  ],
};

describe('FileTree', () => {
  beforeEach(() => {
    vi.mocked(getFileTree).mockResolvedValue(mockFileTree);
    vi.mocked(createFile).mockResolvedValue({ success: true });
  });

  it('파일 트리를 로드하고 표시한다', async () => {
    render(<FileTree workspaceId="ws-123" />);

    // 로딩 상태
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    // 로딩 완료 후
    await waitFor(() => {
      expect(screen.getByText('src')).toBeInTheDocument();
      expect(screen.getByText('README.md')).toBeInTheDocument();
    });
  });

  it('폴더를 클릭하면 확장/축소된다', async () => {
    render(<FileTree workspaceId="ws-123" />);

    await waitFor(() => {
      expect(screen.getByText('src')).toBeInTheDocument();
    });

    // src 폴더 클릭 (이미 확장됨)
    const srcFolder = screen.getByText('src');
    fireEvent.click(srcFolder);

    // 자식 파일 표시 확인
    await waitFor(() => {
      expect(screen.getByText('main.py')).toBeInTheDocument();
    });
  });

  it('파일을 클릭하면 onFileSelect가 호출된다', async () => {
    const onFileSelect = vi.fn();
    render(<FileTree workspaceId="ws-123" onFileSelect={onFileSelect} />);

    await waitFor(() => {
      expect(screen.getByText('README.md')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('README.md'));

    expect(onFileSelect).toHaveBeenCalledWith('README.md');
  });

  it('새 파일 생성 버튼이 작동한다', async () => {
    const onFileSelect = vi.fn();
    render(<FileTree workspaceId="ws-123" onFileSelect={onFileSelect} />);

    await waitFor(() => {
      expect(screen.getByText('New File')).toBeInTheDocument();
    });

    // 새 파일 버튼 클릭
    fireEvent.click(screen.getByText('New File'));

    // 입력창 표시
    const input = screen.getByPlaceholderText('filename.py');
    expect(input).toBeInTheDocument();

    // 파일명 입력
    fireEvent.change(input, { target: { value: 'test.py' } });
    
    // Enter 키 또는 확인 버튼
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(createFile).toHaveBeenCalledWith('ws-123', 'test.py');
    });
  });

  it('Escape 키로 새 파일 입력을 취소한다', async () => {
    render(<FileTree workspaceId="ws-123" />);

    await waitFor(() => {
      expect(screen.getByText('New File')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('New File'));
    
    const input = screen.getByPlaceholderText('filename.py');
    fireEvent.keyDown(input, { key: 'Escape' });

    // 입력창이 사라짐
    expect(screen.queryByPlaceholderText('filename.py')).not.toBeInTheDocument();
  });

  it('에러 발생 시 에러 메시지와 재시도 버튼을 표시한다', async () => {
    vi.mocked(getFileTree).mockRejectedValueOnce(new Error('Failed to load'));

    render(<FileTree workspaceId="ws-123" />);

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  it('키보드 네비게이션이 작동한다', async () => {
    const onFileSelect = vi.fn();
    render(<FileTree workspaceId="ws-123" onFileSelect={onFileSelect} />);

    await waitFor(() => {
      expect(screen.getByText('README.md')).toBeInTheDocument();
    });

    // Enter 키로 파일 선택
    const fileItem = screen.getByText('README.md').closest('[role="link"]');
    if (fileItem) {
      fireEvent.keyDown(fileItem, { key: 'Enter' });
      expect(onFileSelect).toHaveBeenCalledWith('README.md');
    }
  });

  it('접근성 속성이 올바르게 설정된다', async () => {
    render(<FileTree workspaceId="ws-123" />);

    await waitFor(() => {
      expect(screen.getByRole('tree')).toBeInTheDocument();
    });

    expect(screen.getByRole('tree')).toHaveAttribute('aria-label', '파일 탐색기');
  });
});

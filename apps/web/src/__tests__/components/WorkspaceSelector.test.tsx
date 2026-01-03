/**
 * WorkspaceSelector 컴포넌트 테스트
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import WorkspaceSelector from '@/components/WorkspaceSelector';

// Mock API
vi.mock('@/lib/api', () => ({
  cloneGitHubRepository: vi.fn(),
  createWorkspace: vi.fn(),
}));

import { cloneGitHubRepository, createWorkspace } from '@/lib/api';

describe('WorkspaceSelector', () => {
  const mockOnSelect = vi.fn();
  const mockWorkspace = {
    workspaceId: 'ws-123',
    name: 'test-workspace',
    rootPath: '/workspaces/test-workspace',
  };

  beforeEach(() => {
    vi.mocked(cloneGitHubRepository).mockResolvedValue(mockWorkspace);
    vi.mocked(createWorkspace).mockResolvedValue(mockWorkspace);
    mockOnSelect.mockClear();
  });

  it('초기 선택 화면을 표시한다', () => {
    render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

    expect(screen.getByText('워크스페이스 선택')).toBeInTheDocument();
    expect(screen.getByText('GitHub 클론')).toBeInTheDocument();
    expect(screen.getByText('빈 워크스페이스 생성')).toBeInTheDocument();
  });

  describe('GitHub 클론', () => {
    it('GitHub 클론 폼을 표시한다', () => {
      render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

      fireEvent.click(screen.getByText('GitHub 클론'));

      expect(screen.getByText('GitHub 저장소 클론')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('https://github.com/owner/repo')).toBeInTheDocument();
    });

    it('GitHub 저장소를 클론한다', async () => {
      render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

      fireEvent.click(screen.getByText('GitHub 클론'));

      const urlInput = screen.getByPlaceholderText('https://github.com/owner/repo');
      fireEvent.change(urlInput, { target: { value: 'https://github.com/user/repo' } });

      fireEvent.click(screen.getByRole('button', { name: /클론/i }));

      await waitFor(() => {
        expect(cloneGitHubRepository).toHaveBeenCalledWith({
          repositoryUrl: 'https://github.com/user/repo',
          name: undefined,
          branch: undefined,
        });
      });

      await waitFor(() => {
        expect(mockOnSelect).toHaveBeenCalledWith(mockWorkspace);
      });
    });

    it('클론 실패 시 에러를 표시한다', async () => {
      vi.mocked(cloneGitHubRepository).mockRejectedValueOnce(new Error('Clone failed'));

      render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

      fireEvent.click(screen.getByText('GitHub 클론'));

      const urlInput = screen.getByPlaceholderText('https://github.com/owner/repo');
      fireEvent.change(urlInput, { target: { value: 'https://github.com/user/repo' } });

      fireEvent.click(screen.getByRole('button', { name: /클론/i }));

      await waitFor(() => {
        expect(screen.getByText('Clone failed')).toBeInTheDocument();
      });
    });

    it('취소 버튼으로 선택 화면으로 돌아간다', () => {
      render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

      fireEvent.click(screen.getByText('GitHub 클론'));
      expect(screen.getByText('GitHub 저장소 클론')).toBeInTheDocument();

      fireEvent.click(screen.getByText('취소'));
      expect(screen.getByText('워크스페이스 선택')).toBeInTheDocument();
    });
  });

  describe('빈 워크스페이스 생성', () => {
    it('빈 워크스페이스 생성 폼을 표시한다', () => {
      render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

      fireEvent.click(screen.getByText('빈 워크스페이스 생성'));

      expect(screen.getByText('빈 워크스페이스 생성')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('my-project')).toBeInTheDocument();
    });

    it('빈 워크스페이스를 생성한다', async () => {
      render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

      fireEvent.click(screen.getByText('빈 워크스페이스 생성'));

      const nameInput = screen.getByPlaceholderText('my-project');
      fireEvent.change(nameInput, { target: { value: 'new-project' } });

      fireEvent.click(screen.getByRole('button', { name: /생성/i }));

      await waitFor(() => {
        expect(createWorkspace).toHaveBeenCalledWith('new-project');
      });

      await waitFor(() => {
        expect(mockOnSelect).toHaveBeenCalledWith(mockWorkspace);
      });
    });

    it('이름 없이 생성 시 에러를 표시한다', async () => {
      render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

      fireEvent.click(screen.getByText('빈 워크스페이스 생성'));

      // 생성 버튼은 비활성화됨
      const createButton = screen.getByRole('button', { name: /생성/i });
      expect(createButton).toBeDisabled();
    });
  });

  it('접근성 속성이 올바르게 설정된다', () => {
    render(<WorkspaceSelector onWorkspaceSelect={mockOnSelect} />);

    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('워크스페이스 선택');
    expect(screen.getByRole('navigation')).toHaveAttribute('aria-label', '워크스페이스 생성 옵션');
  });
});

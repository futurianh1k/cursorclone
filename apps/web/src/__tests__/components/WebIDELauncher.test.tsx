/**
 * WebIDELauncher 컴포넌트 테스트
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { WebIDELauncher, WebIDELauncherCard } from '../../components/WebIDELauncher'

// API 모킹
vi.mock('../../lib/api', () => ({
  getWorkspaceIDEUrl: vi.fn(),
}))

describe('WebIDELauncher', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('Web IDE 열기 버튼을 렌더링한다', () => {
    render(<WebIDELauncher workspaceId="ws-1" />)
    
    expect(screen.getByText('Web IDE 열기')).toBeInTheDocument()
  })

  it('버튼 클릭 시 IDE URL을 가져온다', async () => {
    const mockGetUrl = vi.fn().mockResolvedValue({
      url: 'http://localhost:8443',
      containerId: null,
      status: 'shared',
    })
    
    const api = await import('../../lib/api')
    ;(api.getWorkspaceIDEUrl as ReturnType<typeof vi.fn>).mockImplementation(mockGetUrl)
    
    // window.open 모킹
    const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    
    render(<WebIDELauncher workspaceId="ws-1" />)
    
    const button = screen.getByText('Web IDE 열기')
    fireEvent.click(button)
    
    await waitFor(() => {
      expect(mockGetUrl).toHaveBeenCalledWith('ws-1')
    })
    
    await waitFor(() => {
      expect(windowOpenSpy).toHaveBeenCalledWith(
        'http://localhost:8443',
        '_blank',
        'noopener,noreferrer'
      )
    })
    
    windowOpenSpy.mockRestore()
  })

  it('로딩 상태를 표시한다', async () => {
    const mockGetUrl = vi.fn().mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 100))
    )
    
    const api = await import('../../lib/api')
    ;(api.getWorkspaceIDEUrl as ReturnType<typeof vi.fn>).mockImplementation(mockGetUrl)
    
    render(<WebIDELauncher workspaceId="ws-1" />)
    
    const button = screen.getByText('Web IDE 열기')
    fireEvent.click(button)
    
    await waitFor(() => {
      expect(screen.getByText('IDE 실행 중...')).toBeInTheDocument()
    })
  })

  it('에러 발생 시 에러 메시지를 표시한다', async () => {
    const mockGetUrl = vi.fn().mockRejectedValue(new Error('연결 실패'))
    
    const api = await import('../../lib/api')
    ;(api.getWorkspaceIDEUrl as ReturnType<typeof vi.fn>).mockImplementation(mockGetUrl)
    
    render(<WebIDELauncher workspaceId="ws-1" />)
    
    const button = screen.getByText('Web IDE 열기')
    fireEvent.click(button)
    
    await waitFor(() => {
      expect(screen.getByText(/연결 실패/)).toBeInTheDocument()
    })
  })
})

describe('WebIDELauncherCard', () => {
  it('카드 형태로 렌더링한다', () => {
    render(<WebIDELauncherCard workspaceId="ws-1" workspaceName="Test" />)
    
    expect(screen.getByText('Web IDE')).toBeInTheDocument()
    expect(screen.getByText('IDE 열기')).toBeInTheDocument()
    expect(screen.getByText(/풀 VS Code 환경/)).toBeInTheDocument()
  })

  it('기능 목록을 표시한다', () => {
    render(<WebIDELauncherCard workspaceId="ws-1" />)
    
    expect(screen.getByText(/터미널 & 디버거/)).toBeInTheDocument()
    expect(screen.getByText(/AI 코딩 지원/)).toBeInTheDocument()
    expect(screen.getByText(/Git 통합/)).toBeInTheDocument()
  })
})

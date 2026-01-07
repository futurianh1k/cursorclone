/**
 * API 클라이언트 테스트
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'

// API 함수들을 직접 테스트
describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as ReturnType<typeof vi.fn>).mockReset()
  })

  describe('listWorkspaces', () => {
    it('워크스페이스 목록을 가져온다', async () => {
      const mockWorkspaces = [
        { workspaceId: 'ws-1', name: 'Test Workspace', rootPath: '/test' }
      ]
      
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockWorkspaces,
      })
      
      // 동적 임포트로 API 모듈 가져오기
      const { listWorkspaces } = await import('../lib/api')
      const result = await listWorkspaces()
      
      expect(result).toEqual(mockWorkspaces)
      expect(global.fetch).toHaveBeenCalled()
      const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
      expect(callArgs[0]).toContain('/api/workspaces')
    })

    it('API 에러 시 예외를 던진다', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found',
        json: async () => ({ detail: { error: 'Not found' } }),
      })
      
      const { listWorkspaces } = await import('../lib/api')
      
      await expect(listWorkspaces()).rejects.toThrow()
    })
  })

  describe('createWorkspace', () => {
    it('새 워크스페이스를 생성한다', async () => {
      const mockWorkspace = {
        workspaceId: 'ws-new',
        projectId: 'prj-1',
        name: 'New Workspace',
        rootPath: '/new'
      }
      
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockWorkspace,
      })
      
      const { createWorkspace } = await import('../lib/api')
      const result = await createWorkspace('New Workspace', 'python')
      
      expect(result).toEqual(mockWorkspace)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/workspaces'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      )
    })

    it('projectId/projectName을 포함해 워크스페이스를 생성한다', async () => {
      const mockWorkspace = {
        workspaceId: 'ws-new',
        projectId: 'prj-1',
        name: 'New Workspace',
        rootPath: '/new'
      }

      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockWorkspace,
      })

      const { createWorkspace } = await import('../lib/api')
      await createWorkspace('New Workspace', { projectId: 'prj-1', projectName: 'My Project', language: 'python' })

      const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0]
      const init = callArgs[1]
      expect(init.method).toBe('POST')
      const body = JSON.parse(init.body)
      expect(body.projectId).toBe('prj-1')
      expect(body.projectName).toBe('My Project')
    })
  })

  describe('Projects API', () => {
    it('updateProject > 프로젝트 이름을 수정한다', async () => {
      const mockProject = { projectId: 'prj_1', name: 'NewName', ownerId: 'u1', orgId: 'o1' }

      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockProject,
      })

      const { updateProject } = await import('../lib/api')
      const result = await updateProject('prj_1', { name: 'NewName', description: 'Desc' })

      expect(result).toEqual(mockProject)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/projects/prj_1'),
        expect.objectContaining({ method: 'PATCH' })
      )
    })

    it('deleteProject > 프로젝트를 삭제한다', async () => {
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      })

      const { deleteProject } = await import('../lib/api')
      await expect(deleteProject('prj_1')).resolves.toBeUndefined()

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/projects/prj_1'),
        expect.objectContaining({ method: 'DELETE' })
      )
    })
  })

  describe('getFileTree', () => {
    it('파일 트리를 가져온다', async () => {
      const mockTree = {
        workspaceId: 'ws-1',
        tree: [
          { name: 'src', path: 'src', type: 'directory', children: [] }
        ]
      }
      
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTree,
      })
      
      const { getFileTree } = await import('../lib/api')
      const result = await getFileTree('ws-1')
      
      expect(result).toEqual(mockTree)
    })
  })

  describe('getFileContent', () => {
    it('파일 내용을 가져온다', async () => {
      const mockContent = {
        path: 'src/main.py',
        content: 'print("Hello")',
        encoding: 'utf-8'
      }
      
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockContent,
      })
      
      const { getFileContent } = await import('../lib/api')
      const result = await getFileContent('ws-1', 'src/main.py')
      
      expect(result).toEqual(mockContent)
    })
  })

  describe('IDE API', () => {
    it('IDE URL을 가져온다', async () => {
      const mockIdeUrl = {
        url: 'http://localhost:8443',
        containerId: null,
        status: 'shared'
      }
      
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockIdeUrl,
      })
      
      const { getWorkspaceIDEUrl } = await import('../lib/api')
      const result = await getWorkspaceIDEUrl('ws-1')
      
      expect(result.url).toBe('http://localhost:8443')
      expect(result.status).toBe('shared')
    })
  })
})

describe('AI API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as ReturnType<typeof vi.fn>).mockReset()
  })

  describe('getAIModes', () => {
    it('AI 모드 목록을 가져온다', async () => {
      const mockModes = {
        modes: [
          { id: 'agent', name: 'Agent', description: '...', icon: '⚡' },
          { id: 'ask', name: 'Ask', description: '...', icon: '💬' },
        ],
        current: 'ask'
      }
      
      ;(global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockModes,
      })
      
      const { getAIModes } = await import('../lib/api')
      const result = await getAIModes()
      
      expect(result.modes).toHaveLength(2)
      expect(result.current).toBe('ask')
    })
  })
})

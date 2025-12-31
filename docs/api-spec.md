# API Spec (MVP)

## Auth
- GET /api/auth/me

## Workspaces
- POST /api/workspaces
- GET /api/workspaces

## Files
- GET /api/workspaces/{wsId}/files
- GET /api/workspaces/{wsId}/files/content?path=...
- PUT /api/workspaces/{wsId}/files/content

## AI
- POST /api/ai/explain
- POST /api/ai/rewrite

## Patch
- POST /api/patch/validate
- POST /api/patch/apply

## WebSocket
- WS /ws/workspaces/{wsId}

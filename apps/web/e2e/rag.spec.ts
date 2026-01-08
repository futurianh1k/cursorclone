import { test, expect } from "@playwright/test";
import { loadState } from "./helpers";

test("gateway RAG stats endpoint works (smoke)", async ({ request }) => {
  const { gatewayUrl, gatewayToken } = loadState();
  const r = await request.get(`${gatewayUrl}/v1/rag/stats`, {
    headers: { Authorization: `Bearer ${gatewayToken}` },
    timeout: 60_000,
  });
  expect(r.status()).toBe(200);
  const body = await r.json();
  expect(body).toHaveProperty("points_count");
  expect(body).toHaveProperty("vectors_count");
});

test("gateway RAG search returns response shape (may be empty)", async ({ request }) => {
  const { gatewayUrl, gatewayToken, workspaceId } = loadState();
  const r = await request.post(`${gatewayUrl}/v1/rag/search`, {
    headers: { Authorization: `Bearer ${gatewayToken}`, "Content-Type": "application/json" },
    data: { query: "main", workspace_id: workspaceId, limit: 5 },
    timeout: 120_000,
  });
  expect(r.status()).toBe(200);
  const body = await r.json();
  expect(body).toHaveProperty("results");
});


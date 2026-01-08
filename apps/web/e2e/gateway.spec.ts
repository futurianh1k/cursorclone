import { test, expect } from "@playwright/test";
import { loadState } from "./helpers";

test("gateway /healthz is reachable", async ({ request }) => {
  const { gatewayUrl } = loadState();
  const r = await request.get(`${gatewayUrl}/healthz`);
  expect(r.status()).toBe(200);
  const body = await r.json();
  expect(body.status).toBe("ok");
});

test("gateway /v1/chat/completions works with workspace-scoped token (smoke)", async ({ request }) => {
  test.slow();
  const { gatewayUrl, gatewayToken } = loadState();
  const model = process.env.E2E_CHAT_MODEL || "Qwen/Qwen2.5-Coder-7B-Instruct";

  const r = await request.post(`${gatewayUrl}/v1/chat/completions`, {
    headers: {
      Authorization: `Bearer ${gatewayToken}`,
      "Content-Type": "application/json",
    },
    data: {
      model,
      messages: [{ role: "user", content: "ping" }],
      max_tokens: 8,
      temperature: 0,
    },
    timeout: 120_000,
  });

  expect(r.status()).toBeLessThan(400);
  const body = await r.json();
  expect(body).toHaveProperty("choices");
});


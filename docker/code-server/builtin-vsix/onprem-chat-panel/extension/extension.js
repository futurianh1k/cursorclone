const vscode = require("vscode");
const fs = require("fs");
const os = require("os");
const path = require("path");

const DEFAULT_MAX_ATTEMPTS = 20;
const DEFAULT_INTERVAL_MS = 500;

async function commandExists(commandId) {
  try {
    const commands = await vscode.commands.getCommands(true);
    return commands.includes(commandId);
  } catch {
    return false;
  }
}

function _b64urlToJson(b64url) {
  // base64url -> base64 (+ padding)
  let b64 = b64url.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4;
  if (pad === 2) b64 += "==";
  else if (pad === 3) b64 += "=";
  else if (pad !== 0) throw new Error("Invalid base64url");
  const s = Buffer.from(b64, "base64").toString("utf8");
  return JSON.parse(s);
}

function decodeJwtPayload(token) {
  const parts = (token || "").split(".");
  if (parts.length < 2) return null;
  try {
    return _b64urlToJson(parts[1]);
  } catch {
    return null;
  }
}

function readJsonIfExists(p) {
  try {
    if (!fs.existsSync(p)) return null;
    const raw = fs.readFileSync(p, "utf8");
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getContinueConfig() {
  const p = path.join(os.homedir(), ".continue", "config.json");
  return readJsonIfExists(p);
}

function getGatewayApiBase() {
  const cfg = vscode.workspace.getConfiguration();
  const fromSetting = cfg.get("cursorOnprem.gateway.apiBase", "");
  if (fromSetting && typeof fromSetting === "string") return fromSetting;
  if (process.env.VLLM_API_ENDPOINT) return process.env.VLLM_API_ENDPOINT;
  const cont = getContinueConfig();
  const apiBase = cont?.models?.[0]?.apiBase;
  return typeof apiBase === "string" ? apiBase : "http://cursor-poc-gateway:8081/v1";
}

function getGatewayToken() {
  const cfg = vscode.workspace.getConfiguration();
  const src = cfg.get("cursorOnprem.gateway.tokenSource", "tabby");

  if (src === "env") {
    return process.env.GATEWAY_TOKEN || "";
  }
  if (src === "continue") {
    const cont = getContinueConfig();
    const apiKey = cont?.models?.[0]?.apiKey;
    return typeof apiKey === "string" ? apiKey : "";
  }
  if (src === "none") return "";

  // default: tabby setting
  const tabbyToken = cfg.get("tabby.api.authToken", "");
  return typeof tabbyToken === "string" ? tabbyToken : "";
}

function getChatModel() {
  const cfg = vscode.workspace.getConfiguration();
  const fromSetting = cfg.get("cursorOnprem.chat.model", "");
  if (fromSetting && typeof fromSetting === "string") return fromSetting;
  const cont = getContinueConfig();
  const m = cont?.models?.[0]?.model;
  return typeof m === "string" ? m : "unknown";
}

async function openContinueOnRight() {
  // Continue provides these commands. We use them instead of poking VS Code internals.
  const toggleAux = "continue.toggleAuxiliaryBar";
  const focusInput = "continue.focusContinueInput";

  const hasToggle = await commandExists(toggleAux);
  const hasFocus = await commandExists(focusInput);
  if (!hasToggle || !hasFocus) {
    throw new Error("Continue commands not available yet");
  }

  // Assumption: default state is "auxiliary bar closed". This opens it on startup.
  await vscode.commands.executeCommand(toggleAux);
  await vscode.commands.executeCommand(focusInput);
}

async function openOpenCodeTerminal() {
  // OpenCode extension provides these commands.
  const openTerminal = "opencode.openTerminal";
  const has = await commandExists(openTerminal);
  if (!has) {
    throw new Error("OpenCode command not available (sst-dev.opencode not installed?)");
  }
  await vscode.commands.executeCommand(openTerminal);
}

async function openLauncherBestEffort() {
  // Try to open our launcher view, and move it to the right sidebar (best-effort).
  // These commands can vary by VS Code/code-server version; never fail hard.
  try {
    // Open our view container
    await vscode.commands.executeCommand("workbench.view.extension.cursorOnpremAgents");
  } catch {}
  try {
    await vscode.commands.executeCommand("workbench.action.openView", "cursorOnprem.launcherView");
  } catch {
    try {
      await vscode.commands.executeCommand("workbench.action.openView", { viewId: "cursorOnprem.launcherView" });
    } catch {}
  }
  try {
    await vscode.commands.executeCommand("workbench.action.moveViewToSecondarySideBar");
  } catch {}
  try {
    await vscode.commands.executeCommand("workbench.action.toggleAuxiliaryBar");
  } catch {}
}

async function openOpenCodeChatView() {
  try {
    await vscode.commands.executeCommand("workbench.view.extension.cursorOnpremAgents");
  } catch {}
  try {
    await vscode.commands.executeCommand("workbench.action.openView", "cursorOnprem.opencodeChatView");
  } catch {
    try {
      await vscode.commands.executeCommand("workbench.action.openView", { viewId: "cursorOnprem.opencodeChatView" });
    } catch {}
  }
  try {
    await vscode.commands.executeCommand("workbench.action.moveViewToSecondarySideBar");
  } catch {}
  try {
    await vscode.commands.executeCommand("workbench.action.toggleAuxiliaryBar");
  } catch {}
}

async function chooseAgentAndApply() {
  const items = [
    { label: "Continue (Right Panel)", value: "continue" },
    { label: "OpenCode (Terminal)", value: "opencode" },
    { label: "Off (Do nothing automatically)", value: "off" },
  ];
  const picked = await vscode.window.showQuickPick(items, {
    placeHolder: "Choose which agent to prefer at startup (offline/on-prem)",
  });
  if (!picked) return;

  const cfg = vscode.workspace.getConfiguration();
  await cfg.update("cursorOnprem.rightPanel.agent", picked.value, vscode.ConfigurationTarget.Global);

  if (picked.value === "continue") {
    await openContinueOnRight();
  } else if (picked.value === "opencode") {
    await openOpenCodeTerminal();
  }
}

async function getStatusSnapshot() {
  const cfg = vscode.workspace.getConfiguration();
  const agent = cfg.get("cursorOnprem.rightPanel.agent", "continue");
  const launcher = cfg.get("cursorOnprem.rightPanel.launcher", true);

  const continueAvailable =
    (await commandExists("continue.toggleAuxiliaryBar")) && (await commandExists("continue.focusContinueInput"));
  const opencodeAvailable = await commandExists("opencode.openTerminal");

  let opencodeCli = false;
  try {
    // Lightweight check: search PATH without executing (best-effort)
    const which = require("child_process").spawnSync("sh", ["-lc", "command -v opencode"], { encoding: "utf8" });
    opencodeCli = which.status === 0 && !!(which.stdout || "").trim();
  } catch {
    opencodeCli = false;
  }

  const apiBase = getGatewayApiBase();
  const token = getGatewayToken();
  const jwt = token ? decodeJwtPayload(token) : null;

  return {
    agent,
    launcherEnabled: !!launcher,
    continueAvailable,
    opencodeAvailable,
    opencodeCliAvailable: opencodeCli,
    gateway: {
      apiBase,
      tokenPresent: !!token,
      claims: jwt
        ? {
            user_id: jwt.sub || null,
            tenant_id: jwt.tid || null,
            project_id: jwt.pid || null,
            workspace_id: jwt.wid || null,
            role: jwt.role || null,
            exp: jwt.exp || null,
          }
        : null,
      model: getChatModel(),
    },
  };
}

function htmlPage(title, bodyHtml, nonce) {
  const csp = [
    "default-src 'none'",
    "img-src data: vscode-resource: https:",
    "style-src 'unsafe-inline'",
    `script-src 'nonce-${nonce}'`,
  ].join("; ");
  return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta http-equiv="Content-Security-Policy" content="${csp}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${title}</title>
  </head>
  <body style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; padding: 10px;">
    ${bodyHtml}
  </body>
</html>`;
}

function getNonce() {
  return Math.random().toString(36).slice(2);
}

class LauncherViewProvider {
  constructor(ctx) {
    this.ctx = ctx;
  }
  resolveWebviewView(view) {
    view.webview.options = { enableScripts: true };
    const nonce = getNonce();
    view.webview.html = htmlPage(
      "On-Prem Agents",
      `
      <h3 style="margin: 0 0 8px 0;">On-Prem Agents</h3>
      <div style="display:flex; gap:8px; flex-wrap: wrap; margin-bottom: 10px;">
        <button id="btnContinue">Continue (Right)</button>
        <button id="btnOpenCode">OpenCode (Terminal)</button>
        <button id="btnChat">OpenCode Chat (Webview)</button>
        <button id="btnChoose">Choose…</button>
        <button id="btnRefresh">Refresh</button>
      </div>
      <pre id="status" style="white-space: pre-wrap; background:#111; color:#ddd; padding:10px; border-radius:6px; overflow:auto; max-height: 60vh;"></pre>
      <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const $ = (id) => document.getElementById(id);
        const render = (s) => { $('status').textContent = JSON.stringify(s, null, 2); };

        window.addEventListener('message', (event) => {
          const msg = event.data;
          if (msg && msg.type === 'status') render(msg.data);
        });

        $('btnContinue').addEventListener('click', () => vscode.postMessage({ type: 'openContinue' }));
        $('btnOpenCode').addEventListener('click', () => vscode.postMessage({ type: 'openOpenCode' }));
        $('btnChat').addEventListener('click', () => vscode.postMessage({ type: 'openOpenCodeChat' }));
        $('btnChoose').addEventListener('click', () => vscode.postMessage({ type: 'chooseAgent' }));
        $('btnRefresh').addEventListener('click', () => vscode.postMessage({ type: 'getStatus' }));

        vscode.postMessage({ type: 'getStatus' });
      </script>
      `,
      nonce
    );

    view.webview.onDidReceiveMessage(async (msg) => {
      try {
        if (msg?.type === "getStatus") {
          const s = await getStatusSnapshot();
          view.webview.postMessage({ type: "status", data: s });
          return;
        }
        if (msg?.type === "openContinue") return await openContinueOnRight();
        if (msg?.type === "openOpenCode") return await openOpenCodeTerminal();
        if (msg?.type === "chooseAgent") return await chooseAgentAndApply();
        if (msg?.type === "openOpenCodeChat") return await openOpenCodeChatView();
      } catch (e) {
        // Never throw to the UI; just refresh status.
        const s = await getStatusSnapshot();
        view.webview.postMessage({ type: "status", data: { ...s, lastError: String(e?.message || e) } });
      }
    });
  }
}

class OpenCodeChatViewProvider {
  constructor(ctx) {
    this.ctx = ctx;
  }

  resolveWebviewView(view) {
    view.webview.options = { enableScripts: true };
    const nonce = getNonce();
    view.webview.html = htmlPage(
      "OpenCode Chat",
      `
      <h3 style="margin: 0 0 8px 0;">OpenCode Chat (On-Prem)</h3>
      <div style="margin-bottom:8px; font-size: 12px; color: #666;">
        - 저장/로그 없음(세션 메모리만)\n
        - LLM/RAG: on-prem Gateway(/v1/chat, /v1/rag/context)
      </div>
      <div style="display:flex; gap:8px; align-items:center; margin-bottom: 8px;">
        <label style="display:flex; gap:6px; align-items:center;">
          <input type="checkbox" id="useRag" checked />
          RAG context 포함
        </label>
        <button id="btnClear">Clear</button>
        <button id="btnStatus">Status</button>
      </div>
      <div id="messages" style="background:#111; color:#ddd; padding:10px; border-radius:6px; overflow:auto; height: 45vh;"></div>
      <div style="display:flex; gap:8px; margin-top: 8px;">
        <textarea id="input" rows="3" style="flex:1; width:100%;"></textarea>
        <button id="btnSend">Send</button>
      </div>
      <pre id="status" style="white-space: pre-wrap; background:#f6f6f6; padding:8px; border-radius:6px; overflow:auto; max-height: 20vh; margin-top: 10px; display:none;"></pre>
      <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const $ = (id) => document.getElementById(id);
        const msgBox = $('messages');
        const statusBox = $('status');
        let buf = [];

        function append(role, text) {
          buf.push({ role, text });
          const div = document.createElement('div');
          div.style.marginBottom = '10px';
          div.innerHTML = '<b>' + role + '</b><br/>' + (text || '').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br/>');
          msgBox.appendChild(div);
          msgBox.scrollTop = msgBox.scrollHeight;
        }

        function setStatus(s) {
          statusBox.style.display = 'block';
          statusBox.textContent = JSON.stringify(s, null, 2);
        }

        window.addEventListener('message', (event) => {
          const msg = event.data;
          if (!msg) return;
          if (msg.type === 'assistant') append('assistant', msg.text);
          if (msg.type === 'error') append('error', msg.text);
          if (msg.type === 'status') setStatus(msg.data);
        });

        $('btnSend').addEventListener('click', () => {
          const text = $('input').value.trim();
          if (!text) return;
          $('input').value = '';
          append('user', text);
          vscode.postMessage({ type: 'chat', text, useRag: $('useRag').checked, history: buf.slice(-12) });
        });
        $('btnClear').addEventListener('click', () => {
          buf = [];
          msgBox.innerHTML = '';
          statusBox.style.display = 'none';
        });
        $('btnStatus').addEventListener('click', () => vscode.postMessage({ type: 'getStatus' }));
      </script>
      `,
      nonce
    );

    view.webview.onDidReceiveMessage(async (msg) => {
      if (msg?.type === "getStatus") {
        const s = await getStatusSnapshot();
        view.webview.postMessage({ type: "status", data: s });
        return;
      }
      if (msg?.type === "chat") {
        const text = String(msg.text || "").trim();
        const useRag = !!msg.useRag;
        const history = Array.isArray(msg.history) ? msg.history : [];
        try {
          const answer = await runGatewayChat({ text, useRag, history });
          view.webview.postMessage({ type: "assistant", text: answer });
        } catch (e) {
          view.webview.postMessage({ type: "error", text: String(e?.message || e) });
        }
      }
    });
  }
}

async function runGatewayChat({ text, useRag, history }) {
  const apiBase = getGatewayApiBase();
  const token = getGatewayToken();
  if (!token) throw new Error("Gateway token not found. Set tabby.api.authToken or Continue config apiKey.");

  const jwt = decodeJwtPayload(token);
  const workspaceId = jwt?.wid;
  if (!workspaceId) throw new Error("Cannot determine workspace_id from token (wid claim missing).");

  const model = getChatModel();
  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

  let systemContext = "";
  if (useRag) {
    const ragUrl = `${apiBase.replace(/\\/+$/,'')}/rag/context`;
    const ragReq = {
      query: text,
      workspace_id: workspaceId,
      max_results: 8,
      include_file_tree: false,
      task_type: "chat",
      max_context_chars: 80000,
    };
    const r = await fetch(ragUrl, { method: "POST", headers, body: JSON.stringify(ragReq) });
    if (!r.ok) {
      const t = await r.text();
      throw new Error(`RAG context failed (${r.status}): ${t.slice(0, 400)}`);
    }
    const body = await r.json();
    if (body?.prompt) systemContext = String(body.prompt);
  }

  const chatUrl = `${apiBase.replace(/\\/+$/,'')}/chat/completions`;
  const messages = [];
  if (systemContext) {
    messages.push({ role: "system", content: `You are an on-prem coding assistant. Use the following RAG context:\\n\\n${systemContext}` });
  }
  // Keep last N turns
  for (const h of history) {
    const role = h?.role;
    const content = h?.text;
    if (role === "user" || role === "assistant") messages.push({ role, content: String(content || "") });
  }
  // Ensure current user message is last
  messages.push({ role: "user", content: text });

  const payload = {
    model,
    messages,
    stream: false,
    temperature: 0.2,
  };

  const r2 = await fetch(chatUrl, { method: "POST", headers, body: JSON.stringify(payload) });
  const raw = await r2.text();
  if (!r2.ok) throw new Error(`Chat failed (${r2.status}): ${raw.slice(0, 400)}`);
  const json = JSON.parse(raw);
  const content = json?.choices?.[0]?.message?.content;
  return typeof content === "string" ? content : raw.slice(0, 2000);
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  const disposableContinue = vscode.commands.registerCommand(
    "cursorOnprem.openContinueOnRight",
    async () => {
      await openContinueOnRight();
    }
  );
  const disposableOpenCode = vscode.commands.registerCommand(
    "cursorOnprem.openOpenCode",
    async () => {
      await openOpenCodeTerminal();
    }
  );
  const disposableChoose = vscode.commands.registerCommand(
    "cursorOnprem.chooseRightPanelAgent",
    async () => {
      await chooseAgentAndApply();
    }
  );
  const disposableLauncher = vscode.commands.registerCommand("cursorOnprem.openLauncher", async () => {
    await openLauncherBestEffort();
  });
  const disposableOpenCodeChat = vscode.commands.registerCommand("cursorOnprem.openOpenCodeChat", async () => {
    await openOpenCodeChatView();
  });

  // Webviews
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("cursorOnprem.launcherView", new LauncherViewProvider(context), {
      webviewOptions: { retainContextWhenHidden: true },
    })
  );
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("cursorOnprem.opencodeChatView", new OpenCodeChatViewProvider(context), {
      webviewOptions: { retainContextWhenHidden: true },
    })
  );

  context.subscriptions.push(
    disposableContinue,
    disposableOpenCode,
    disposableChoose,
    disposableLauncher,
    disposableOpenCodeChat
  );

  // Auto-open on startup (best-effort, retry for a few seconds)
  let attempts = 0;
  const timer = setInterval(async () => {
    attempts += 1;
    try {
      const agent = vscode.workspace
        .getConfiguration()
        .get("cursorOnprem.rightPanel.agent", "continue");
      const launcherEnabled = vscode.workspace
        .getConfiguration()
        .get("cursorOnprem.rightPanel.launcher", true);

      if (launcherEnabled) {
        await openLauncherBestEffort();
      }

      if (agent === "off") {
        clearInterval(timer);
        return;
      }

      if (agent === "opencode") {
        await openOpenCodeTerminal();
      } else {
        await openContinueOnRight();
      }
      clearInterval(timer);
    } catch {
      if (attempts >= DEFAULT_MAX_ATTEMPTS) {
        clearInterval(timer);
      }
    }
  }, DEFAULT_INTERVAL_MS);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });
}

function deactivate() {}

module.exports = { activate, deactivate };


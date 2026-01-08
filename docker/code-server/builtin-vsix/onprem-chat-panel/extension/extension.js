const vscode = require("vscode");

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
  context.subscriptions.push(disposableContinue, disposableOpenCode, disposableChoose);

  // Auto-open on startup (best-effort, retry for a few seconds)
  let attempts = 0;
  const timer = setInterval(async () => {
    attempts += 1;
    try {
      const agent = vscode.workspace
        .getConfiguration()
        .get("cursorOnprem.rightPanel.agent", "continue");

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


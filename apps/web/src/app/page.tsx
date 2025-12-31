"use client";

import Editor from "@monaco-editor/react";

export default function Home() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "280px 1fr 360px", height: "100vh" }}>
      <aside style={{ borderRight: "1px solid #ddd", padding: 12 }}>
        <h3>File Tree (stub)</h3>
        <div style={{ fontSize: 12, color: "#666" }}>다음 단계: /api/workspaces/{`{wsId}`}/files 연동</div>
      </aside>

      <main style={{ borderRight: "1px solid #ddd" }}>
        <Editor
          height="100%"
          defaultLanguage="python"
          defaultValue={'print("hello on-prem poc")\n'}
          options={{ minimap: { enabled: false }, fontSize: 14 }}
        />
      </main>

      <section style={{ padding: 12 }}>
        <h3>AI Chat (stub)</h3>
        <div style={{ fontSize: 12, color: "#666" }}>
          다음 단계: /api/ai/rewrite 호출 → diff preview → /api/patch/apply
        </div>
      </section>
    </div>
  );
}

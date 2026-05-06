import { useNavigate } from "react-router-dom";
import { PromptComposer } from "../components/PromptComposer";
import { SidebarRail } from "../components/SidebarRail";

export function TemplateExplorePage() {
  const nav = useNavigate();
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <SidebarRail />
      <main style={{ flex: 1, padding: 24 }}>
        <h1 style={{ textAlign: "center" }}>Replica AI 幻灯片</h1>
        <div style={{ maxWidth: 760, margin: "24px auto" }}>
          <PromptComposer
            onSubmit={() => {
              nav("/workspace");
            }}
          />
        </div>
        <section style={{ marginTop: 32 }}>
          <h3>探索</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                style={{
                  border: "1px solid #eee",
                  borderRadius: 10,
                  height: 120,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                }}
              >
                模板 {i + 1}
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}


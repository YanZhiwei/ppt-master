import { useEffect, useRef, useState } from "react";
import { SidebarRail } from "../components/SidebarRail";
import { PromptComposer } from "../components/PromptComposer";
import { connectSessionEvents, WorkflowEvent } from "../lib/events";
import { createSession, sendSessionMessage } from "../lib/api";

export function WorkspacePage() {
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string>("");
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    sourceRef.current = connectSessionEvents(sessionId, (evt) => {
      setEvents((prev) => [...prev.slice(-49), evt]);
    });
    sourceRef.current.onerror = () => {
      setError("事件流连接失败，请确认后端已启动并可访问 /api");
    };
    return () => {
      sourceRef.current?.close();
    };
  }, [sessionId]);

  async function handleSubmit(text: string) {
    try {
      setError("");
      const sid = sessionId || (await createSession("Replica Workspace Session")).session_id;
      if (!sessionId) setSessionId(sid);
      // Send prompt then confirm once, so workflow can move past blocking gate.
      await sendSessionMessage(sid, text || "生成一个演示文稿", "prompt");
      await sendSessionMessage(sid, "确认八项建议，继续执行", "confirm");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <SidebarRail />
      <main style={{ flex: 1, display: "grid", gridTemplateColumns: "42% 58%" }}>
        <section style={{ borderRight: "1px solid #eee", padding: 16 }}>
          <h3>任务流</h3>
          {error ? <div style={{ color: "#c00", fontSize: 12, marginBottom: 8 }}>{error}</div> : null}
          <div style={{ fontSize: 12, color: "#666", marginBottom: 8 }}>
            {sessionId ? `Session: ${sessionId}` : "Session: 未创建（首次点击对话自动创建）"}
          </div>
          <div style={{ border: "1px solid #f0f0f0", borderRadius: 10, padding: 12, minHeight: 280 }}>
            {events.length === 0 ? (
              <div style={{ fontSize: 13, color: "#777" }}>暂无事件，等待会话状态推送...</div>
            ) : (
              events.map((e) => (
                <div key={e.event_id} style={{ padding: "6px 0", borderBottom: "1px dashed #f2f2f2", fontSize: 12 }}>
                  [{e.phase}] {e.event}
                </div>
              ))
            )}
          </div>
          <div style={{ marginTop: 16 }}>
            <PromptComposer onSubmit={handleSubmit} />
          </div>
        </section>
        <section style={{ padding: 16 }}>
          <h3>预览</h3>
          <div style={{ border: "1px solid #eee", borderRadius: 10, padding: 12, minHeight: 520 }}>
            <div style={{ width: "100%", aspectRatio: "16 / 9", border: "1px solid #ddd", borderRadius: 8 }} />
            <div style={{ marginTop: 12, fontSize: 12, color: "#666" }}>
              右侧为幻灯片预览区（可接实际 SVG/HTML 预览源）
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

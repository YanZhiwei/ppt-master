export function SidebarRail() {
  const items = ["New", "AI 幻灯片", "首页", "Clay", "工作流", "团队"];
  return (
    <aside style={{ width: 72, borderRight: "1px solid #eee", padding: 12 }}>
      {items.map((it) => (
        <div key={it} style={{ margin: "12px 0", fontSize: 12 }}>
          {it}
        </div>
      ))}
    </aside>
  );
}


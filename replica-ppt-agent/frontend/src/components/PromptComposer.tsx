type Props = {
  onSubmit?: (text: string) => void;
  submitLabel?: string;
};

import { useState } from "react";

export function PromptComposer({ onSubmit, submitLabel = "对话" }: Props) {
  const [text, setText] = useState("");
  return (
    <div style={{ border: "1px solid #ddd", borderRadius: 12, padding: 12 }}>
      <textarea
        placeholder="请输入您的演示文稿主题和要求..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        style={{ width: "100%", minHeight: 80, border: "none", outline: "none", resize: "vertical" }}
      />
      <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between" }}>
        <span>Standard</span>
        <button
          onClick={() => {
            onSubmit?.(text);
          }}
        >
          {submitLabel}
        </button>
      </div>
    </div>
  );
}

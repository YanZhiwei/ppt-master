import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { TemplateExplorePage } from "./pages/TemplateExplorePage";
import { WorkspacePage } from "./pages/WorkspacePage";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/explore" replace />} />
        <Route path="/explore" element={<TemplateExplorePage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);


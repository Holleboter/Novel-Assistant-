import { useMemo, useState } from "react";
import { BookOpen, Network, Settings, Sparkles } from "lucide-react";
import { createApiClient } from "./api/client";
import { CreationWorkbench } from "./pages/CreationWorkbench";
import { GraphCenter } from "./pages/GraphCenter";
import { ProjectHub } from "./pages/ProjectHub";
import { SettingsPage } from "./pages/SettingsPage";

type Route =
  | { name: "hub" }
  | { name: "workbench"; projectId: string }
  | { name: "graph" }
  | { name: "settings" };

export function App() {
  const [route, setRoute] = useState<Route>({ name: "hub" });
  const api = useMemo(() => createApiClient(), []);

  return (
    <div className="app-shell">
      <aside className="app-nav" aria-label="主导航">
        <div className="brand-mark">
          <Sparkles size={22} aria-hidden="true" />
          <span>Novel Assistant</span>
        </div>
        <button
          className={route.name === "hub" ? "nav-item active" : "nav-item"}
          onClick={() => setRoute({ name: "hub" })}
        >
          <BookOpen size={18} aria-hidden="true" />
          <span>项目</span>
        </button>
        <button
          className={route.name === "graph" ? "nav-item active" : "nav-item"}
          onClick={() => setRoute({ name: "graph" })}
        >
          <Network size={18} aria-hidden="true" />
          <span>图谱</span>
        </button>
        <button
          className={route.name === "settings" ? "nav-item active" : "nav-item"}
          onClick={() => setRoute({ name: "settings" })}
        >
          <Settings size={18} aria-hidden="true" />
          <span>设置</span>
        </button>
      </aside>
      <main className="app-main">
        {route.name === "hub" ? (
          <ProjectHub api={api} onOpenProject={(projectId) => setRoute({ name: "workbench", projectId })} />
        ) : null}
        {route.name === "workbench" ? (
          <CreationWorkbench api={api} projectId={route.projectId} onBack={() => setRoute({ name: "hub" })} />
        ) : null}
        {route.name === "graph" ? <GraphCenter /> : null}
        {route.name === "settings" ? <SettingsPage api={api} /> : null}
      </main>
    </div>
  );
}

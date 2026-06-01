import { useMemo, useState } from "react";
import { BookOpen, Network, Settings, Sparkles, WandSparkles } from "lucide-react";
import { createApiClient } from "./api/client";
import { CreationWorkbench } from "./pages/CreationWorkbench";
import { GraphCenter } from "./pages/GraphCenter";
import { ProjectHub } from "./pages/ProjectHub";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillsPage } from "./pages/SkillsPage";
import type { PrimaryRouteName } from "./view-models/navigation";
import { primaryNavigationItems } from "./view-models/navigation";

type Route =
  | { name: PrimaryRouteName }
  | { name: "workbench"; projectId: string };

const navIcons = {
  hub: BookOpen,
  skills: WandSparkles,
  graph: Network,
  settings: Settings,
};

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
        {primaryNavigationItems.map((item) => {
          const Icon = navIcons[item.route];
          return (
            <button
              className={route.name === item.route ? "nav-item active" : "nav-item"}
              key={item.route}
              onClick={() => setRoute({ name: item.route })}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </aside>
      <main className="app-main">
        {route.name === "hub" ? (
          <ProjectHub
            api={api}
            onOpenProject={(projectId) => setRoute({ name: "workbench", projectId })}
          />
        ) : null}
        {route.name === "workbench" ? (
          <CreationWorkbench
            api={api}
            projectId={route.projectId}
            onBack={() => setRoute({ name: "hub" })}
          />
        ) : null}
        {route.name === "skills" ? <SkillsPage api={api} /> : null}
        {route.name === "graph" ? <GraphCenter /> : null}
        {route.name === "settings" ? <SettingsPage api={api} /> : null}
      </main>
    </div>
  );
}

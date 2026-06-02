import { useMemo, useState } from "react";
import {
  BookOpen,
  ClipboardList,
  Network,
  Settings,
  Sparkles,
  WandSparkles,
} from "lucide-react";
import { createApiClient } from "./api/client";
import { BlueprintCenter } from "./pages/BlueprintCenter";
import { CreationWorkbench } from "./pages/CreationWorkbench";
import { GraphCenter } from "./pages/GraphCenter";
import { ProjectHub } from "./pages/ProjectHub";
import { SettingsPage } from "./pages/SettingsPage";
import { SkillsPage } from "./pages/SkillsPage";
import type { PrimaryRouteName } from "./view-models/navigation";
import { primaryNavigationItems } from "./view-models/navigation";

type Route =
  | { name: PrimaryRouteName; projectId?: string }
  | { name: "workbench"; projectId: string };

const navIcons = {
  hub: BookOpen,
  blueprint: ClipboardList,
  skills: WandSparkles,
  graph: Network,
  settings: Settings,
};

export function App() {
  const [route, setRoute] = useState<Route>({ name: "hub" });
  const [activeProjectId, setActiveProjectId] = useState("");
  const api = useMemo(() => createApiClient(), []);
  const currentProjectId =
    activeProjectId || ("projectId" in route ? route.projectId : undefined);

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
              onClick={() =>
                setRoute(
                  item.route === "blueprint" && currentProjectId
                    ? { name: "blueprint", projectId: currentProjectId }
                    : { name: item.route },
                )
              }
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
            onOpenProject={(projectId) => {
              setActiveProjectId(projectId);
              setRoute({ name: "workbench", projectId });
            }}
          />
        ) : null}
        {route.name === "workbench" ? (
          <CreationWorkbench
            api={api}
            projectId={route.projectId}
            onBack={() => setRoute({ name: "hub" })}
            onOpenBlueprint={() => setRoute({ name: "blueprint", projectId: route.projectId })}
          />
        ) : null}
        {route.name === "blueprint" ? (
          <BlueprintCenter
            api={api}
            projectId={activeProjectId || route.projectId}
            onProjectChange={(projectId) => setActiveProjectId(projectId)}
            onOpenWorkbench={(projectId) => {
              setActiveProjectId(projectId);
              setRoute({ name: "workbench", projectId });
            }}
          />
        ) : null}
        {route.name === "skills" ? <SkillsPage api={api} /> : null}
        {route.name === "graph" ? <GraphCenter /> : null}
        {route.name === "settings" ? <SettingsPage api={api} /> : null}
      </main>
    </div>
  );
}

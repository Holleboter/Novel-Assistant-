export type PrimaryRouteName =
  | "hub"
  | "blueprint"
  | "skills"
  | "graph"
  | "settings";

export type PrimaryNavigationItem = {
  route: PrimaryRouteName;
  label: string;
};

export const primaryNavigationItems: PrimaryNavigationItem[] = [
  { route: "hub", label: "项目" },
  { route: "blueprint", label: "蓝图" },
  { route: "skills", label: "Skills" },
  { route: "graph", label: "图谱" },
  { route: "settings", label: "设置" },
];

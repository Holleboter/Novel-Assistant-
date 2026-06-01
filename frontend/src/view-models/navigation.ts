export type PrimaryRouteName = "hub" | "skills" | "graph" | "settings";

export type PrimaryNavigationItem = {
  route: PrimaryRouteName;
  label: string;
};

export const primaryNavigationItems: PrimaryNavigationItem[] = [
  { route: "hub", label: "项目" },
  { route: "skills", label: "Skills" },
  { route: "graph", label: "图谱" },
  { route: "settings", label: "设置" },
];

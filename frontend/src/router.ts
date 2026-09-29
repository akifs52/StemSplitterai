import type { ViewName } from "./types";

export const ROUTES: Record<ViewName, { path: string; title: string }> = {
  dashboard: {
    path: "/dashboard",
    title: "StemSplit AI — Dashboard"
  },
  mixer: {
    path: "/mixer",
    title: "StemSplit AI — Stem Mixer"
  },
  settings: {
    path: "/settings",
    title: "StemSplit AI — Settings"
  },
  login: {
    path: "/login",
    title: "StemSplit AI — Sign In"
  },
  register: {
    path: "/register",
    title: "StemSplit AI — Create Account"
  }
};

export function getViewFromPath(pathname: string): ViewName {
  const clean = pathname.toLowerCase().replace(/\/+$/, "") || "/";
  if (clean === "/login") return "login";
  if (clean === "/register") return "register";
  if (clean === "/mixer") return "mixer";
  if (clean === "/settings") return "settings";
  return "dashboard";
}

export function syncRoute(view: ViewName, replace = false): void {
  const route = ROUTES[view];
  if (!route) return;

  const currentPath = window.location.pathname.toLowerCase().replace(/\/+$/, "") || "/";
  const targetPath = route.path;

  if (currentPath !== targetPath) {
    if (replace) {
      window.history.replaceState({ view }, "", targetPath);
    } else {
      window.history.pushState({ view }, "", targetPath);
    }
  }

  document.title = route.title;
}

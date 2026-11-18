import "./style.css";
import { loadJson } from "./data";
import { parseRoute, type Route } from "./router";
import { esc } from "./ui";
import { renderStatus, type ProbeReport } from "./views/status";

const TABS = [
  { view: "spiele", href: "#spiele", label: "Spiele", icon: '<rect x="3" y="5" width="18" height="16" rx="3" stroke="currentColor" stroke-width="2" fill="none"/><path d="M3 10h18M8 3v4M16 3v4" stroke="currentColor" stroke-width="2"/>' },
  { view: "teams", href: "#teams", label: "Teams", icon: '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" stroke="currentColor" stroke-width="2" fill="none"/>' },
  { view: "status", href: "#status", label: "Status", icon: '<circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="2" fill="none"/><path d="M8 12l3 3 5-6" stroke="currentColor" stroke-width="2" fill="none"/>' },
];

const tabOf = (r: Route): string => (r.view === "spiel" ? "spiele" : r.view === "team" ? "teams" : r.view);

export function header(title: string, sub: string, back?: string): void {
  document.getElementById("hdr")!.innerHTML =
    (back ? `<a class="back" href="${esc(back)}" aria-label="Zurück">‹</a>` : "") +
    `<div style="min-width:0"><div class="sub">${esc(sub)}</div><h1>${esc(title)}</h1></div>`;
}

async function viewFor(route: Route): Promise<string> {
  if (route.view === "status") {
    header("Status", "Quellen-Check");
    return renderStatus(await loadJson<ProbeReport>("status/probe.json"), new Date());
  }
  header(route.view === "teams" || route.view === "team" ? "Teams" : "Spiele", "Matchplan");
  return `<section class="card"><p class="muted">Dieser Bereich kommt mit dem nächsten Update.</p></section>`;
}

async function render(): Promise<void> {
  const route = parseRoute(location.hash);
  const tab = tabOf(route);
  document.getElementById("tabs")!.innerHTML = TABS.map(
    (t) => `<a href="${t.href}" ${t.view === tab ? 'aria-current="page"' : ""}><svg viewBox="0 0 24 24">${t.icon}</svg>${t.label}</a>`,
  ).join("");
  const root = document.getElementById("app")!;
  try {
    root.innerHTML = await viewFor(route);
  } catch {
    root.innerHTML = `<section class="card"><p class="muted">Diese Seite konnte nicht geladen werden.</p></section>`;
  }
  window.scrollTo(0, 0);
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => undefined);
window.addEventListener("hashchange", () => void render());
void render();

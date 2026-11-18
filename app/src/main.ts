import "./style.css";
import { loadJson, type FotmobMatch, type History, type Lineups, type Matchday, type Season, type Table, type TeamStats } from "./data";
import { legendFor } from "./legend";
import { parseRoute, type Route } from "./router";
import { esc } from "./ui";
import { renderMatch, renderMatchday } from "./views/spiele";
import { renderStatus, type ProbeReport } from "./views/status";
import { renderTable, renderTeam } from "./views/teams";

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

const NO_DATA = `<section class="card"><p class="muted">Noch keine Daten vorhanden. Der Datenabruf läuft mehrmals täglich.</p></section>`;

async function allMatchdays(): Promise<Matchday[]> {
  const mds = await Promise.all(Array.from({ length: 34 }, (_, i) => loadJson<Matchday>(`matchdays/${i + 1}.json`)));
  return mds.filter((m): m is Matchday => m !== null);
}

async function viewFor(route: Route): Promise<string> {
  if (route.view === "status") {
    header("Status", "Quellen-Check");
    return renderStatus(await loadJson<ProbeReport>("status/probe.json"), new Date());
  }
  const season = await loadJson<Season>("season.json");
  if (!season) {
    header(route.view === "teams" || route.view === "team" ? "Teams" : "Spiele", "Matchplan");
    return NO_DATA;
  }

  if (route.view === "spiele") {
    const md = route.matchday ?? season.current_matchday;
    header(`${md}. Spieltag`, "1. Bundesliga · Saison 26/27");
    const day = await loadJson<Matchday>(`matchdays/${md}.json`);
    return renderMatchday(md, day?.matches ?? [], season);
  }

  if (route.view === "spiel") {
    const mds = await allMatchdays();
    const day = mds.find((d) => d.matches.some((m) => m.id === route.id));
    const match = day?.matches.find((m) => m.id === route.id);
    if (!day || !match) {
      header("Spiel", "Nicht gefunden", "#spiele");
      return NO_DATA;
    }
    const h = season.teams[match.home]?.short ?? match.home;
    const a = season.teams[match.away]?.short ?? match.away;
    header(`${h} – ${a}`, `${day.matchday}. Spieltag`, `#spiele/${day.matchday}`);
    const lineups = !match.finished ? await loadJson<Lineups>("lineups/current.json") : null;
    const fitting = lineups && lineups.matchday === day.matchday ? lineups : null;
    const history = fitting ? await loadJson<History>(`lineups/history-${season.season}-${day.matchday}.json`) : null;
    const fm = match.finished ? await loadJson<FotmobMatch>(`fotmob/${match.id}.json`) : null;
    return renderMatch(match, season, fitting, history, fm);
  }

  const table = await loadJson<Table>("table.json");
  if (route.view === "teams") {
    header("Tabelle", "1. Bundesliga · Saison 26/27");
    return table ? renderTable(table.rows, season) : NO_DATA;
  }

  const t = season.teams[route.key];
  header(t?.short ?? route.key, "Teamprofil", "#teams");
  if (!t) return NO_DATA;
  const [mds, lineups] = await Promise.all([allMatchdays(), loadJson<Lineups>("lineups/current.json")]);
  return renderTeam(route.key, season, table?.rows ?? [], mds.flatMap((d) => d.matches), lineups);
}

async function render(): Promise<void> {
  const route = parseRoute(location.hash);
  const tab = tabOf(route);
  document.getElementById("tabs")!.innerHTML = TABS.map(
    (t) => `<a href="${t.href}" ${t.view === tab ? 'aria-current="page"' : ""}><svg viewBox="0 0 24 24">${t.icon}</svg>${t.label}</a>`,
  ).join("");
  const root = document.getElementById("app")!;
  try {
    const html = await viewFor(route);
    root.innerHTML = html + legendFor(html);
  } catch {
    root.innerHTML = `<section class="card"><p class="muted">Diese Seite konnte nicht geladen werden.</p></section>`;
  }
  window.scrollTo(0, 0);
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => undefined);
window.addEventListener("hashchange", () => void render());
void render();

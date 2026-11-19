import "./style.css";
import { loadJson, type ModelCheck, type Predictions, type PlayerIndex, type PlayerProfile, type FotmobMatch, type History, type Lineups, type Matchday, type Season, type Table, type TeamStats } from "./data";
import { legendFor } from "./legend";
import { parseRoute, type Route } from "./router";
import { esc } from "./ui";
import { renderMatch, renderMatchday } from "./views/spiele";
import { renderStatus, type ProbeReport } from "./views/status";
import { renderTable, renderTeam } from "./views/teams";
import { renderTeamStats } from "./views/teamstats";
import { renderAllResults, renderModelCheck } from "./views/prognose";
import { normSearch, renderPlayer, renderPlayerList, renderSquad } from "./views/players";

const TABS = [
  { view: "spiele", href: "#spiele", label: "Spiele", icon: '<rect x="3" y="5" width="18" height="16" rx="3" stroke="currentColor" stroke-width="2" fill="none"/><path d="M3 10h18M8 3v4M16 3v4" stroke="currentColor" stroke-width="2"/>' },
  { view: "teams", href: "#teams", label: "Teams", icon: '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" stroke="currentColor" stroke-width="2" fill="none"/>' },
  { view: "spieler", href: "#spieler", label: "Spieler", icon: '<circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2" fill="none"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6" stroke="currentColor" stroke-width="2" fill="none"/>' },
  { view: "status", href: "#status", label: "Status", icon: '<circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="2" fill="none"/><path d="M8 12l3 3 5-6" stroke="currentColor" stroke-width="2" fill="none"/>' },
];

const tabOf = (r: Route): string => (r.view === "spiel" || r.view === "prognose" ? "spiele" : r.view === "team" ? "teams" : r.view);

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
    const [probe, model] = await Promise.all([loadJson<ProbeReport>("status/probe.json"), loadJson<ModelCheck>("model.json")]);
    return renderStatus(probe, new Date()) + renderModelCheck(model);
  }
  const season = await loadJson<Season>("season.json");
  if (route.view === "spieler") {
    if (!season) {
      header("Spieler", "Matchplan");
      return NO_DATA;
    }
    const idx = await loadJson<PlayerIndex>("players.json");
    if (route.id) {
      const row = idx?.players.find((r) => r.id === route.id) ?? null;
      header(row?.name ?? "Spieler", "Spielerprofil", "#spieler");
      return renderPlayer(await loadJson<PlayerProfile>(`players/${route.id}.json`), row, season);
    }
    header("Spieler", "1. Bundesliga · Saison 26/27");
    return idx ? renderPlayerList(idx.players, season, "") : NO_DATA;
  }
  if (!season) {
    header(route.view === "teams" || route.view === "team" ? "Teams" : "Spiele", "Matchplan");
    return NO_DATA;
  }

  if (route.view === "spiele") {
    const md = route.matchday ?? season.current_matchday;
    header(`${md}. Spieltag`, "1. Bundesliga · Saison 26/27");
    const [day, preds] = await Promise.all([loadJson<Matchday>(`matchdays/${md}.json`), loadJson<Predictions>(`predictions/${md}.json`)]);
    return renderMatchday(md, day?.matches ?? [], season, preds);
  }

  if (route.view === "spiel" || route.view === "prognose") {
    const mds = await allMatchdays();
    const day = mds.find((d) => d.matches.some((m) => m.id === route.id));
    const match = day?.matches.find((m) => m.id === route.id);
    if (!day || !match) {
      header("Spiel", "Nicht gefunden", "#spiele");
      return NO_DATA;
    }
    const h = season.teams[match.home]?.short ?? match.home;
    const a = season.teams[match.away]?.short ?? match.away;
    const preds = await loadJson<Predictions>(`predictions/${day.matchday}.json`);
    const pred = preds?.matches[String(match.id)] ?? null;
    if (route.view === "prognose") {
      header("Alle Ergebnisse", `${h} – ${a}`, `#spiel/${match.id}`);
      return pred?.probs ? renderAllResults(match, pred, season) : NO_DATA;
    }
    header(`${h} – ${a}`, `${day.matchday}. Spieltag`, `#spiele/${day.matchday}`);
    const lineups = !match.finished ? await loadJson<Lineups>("lineups/current.json") : null;
    const fitting = lineups && lineups.matchday === day.matchday ? lineups : null;
    const history = fitting ? await loadJson<History>(`lineups/history-${season.season}-${day.matchday}.json`) : null;
    const fm = match.finished ? await loadJson<FotmobMatch>(`fotmob/${match.id}.json`) : null;
    return renderMatch(match, season, fitting, history, fm, pred);
  }

  const table = await loadJson<Table>("table.json");
  if (route.view === "teams") {
    header("Tabelle", "1. Bundesliga · Saison 26/27");
    return table ? renderTable(table.rows, season) : NO_DATA;
  }

  const t = season.teams[route.key];
  header(t?.short ?? route.key, "Teamprofil", "#teams");
  if (!t) return NO_DATA;
  const [mds, lineups, ts, idx] = await Promise.all([allMatchdays(), loadJson<Lineups>("lineups/current.json"), loadJson<TeamStats>("teamstats.json"), loadJson<PlayerIndex>("players.json")]);
  return renderTeam(route.key, season, table?.rows ?? [], mds.flatMap((d) => d.matches), lineups, (ts ? renderTeamStats(route.key, ts) : "") + (idx ? renderSquad(idx.players, route.key) : ""));
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
    const search = document.getElementById("psearch") as HTMLInputElement | null;
    search?.addEventListener("input", () => {
      const q = normSearch(search.value.trim());
      root.querySelectorAll<HTMLElement>(".pgroup").forEach((g) => {
        let any = false;
        g.querySelectorAll<HTMLElement>("a.item").forEach((a) => {
          const hit = !q || (a.dataset.s ?? "").includes(q);
          a.hidden = !hit;
          any ||= hit;
        });
        g.hidden = !any;
      });
    });
  } catch {
    root.innerHTML = `<section class="card"><p class="muted">Diese Seite konnte nicht geladen werden.</p></section>`;
  }
  window.scrollTo(0, 0);
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => undefined);
window.addEventListener("hashchange", () => void render());
void render();

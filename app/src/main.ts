import "./style.css";
import { loadJson, type Referees, type SimilarFile, type ScoutReport, type ModelCheck, type Predictions, type PlayerIndex, type PlayerProfile, type FotmobMatch, type History, type Lineups, type Matchday, type Season, type Table, type TeamStats } from "./data";
import { legendFor } from "./legend";
import { parseRoute, type Route } from "./router";
import { esc } from "./ui";
import { renderMatch, renderMatchday } from "./views/spiele";
import { renderStatus, type ProbeReport } from "./views/status";
import { renderTable, renderTeam } from "./views/teams";
import { renderMetricRanking, renderTeamStats } from "./views/teamstats";
import { renderAllResults, renderModelCheck } from "./views/prognose";
import { renderReport, renderScoutPicker } from "./views/scouting";
import { readFav, renderVerein, writeFav } from "./views/verein";
import { normSearch, renderPlayer, renderPlayerList, renderSquad } from "./views/players";

const TABS = [
  { view: "verein", href: "#verein", label: "Mein Verein", icon: '<path d="M4 11l8-7 8 7v9a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z" stroke="currentColor" stroke-width="2" fill="none"/>' },
  { view: "spiele", href: "#spiele", label: "Spiele", icon: '<rect x="3" y="5" width="18" height="16" rx="3" stroke="currentColor" stroke-width="2" fill="none"/><path d="M3 10h18M8 3v4M16 3v4" stroke="currentColor" stroke-width="2"/>' },
  { view: "teams", href: "#teams", label: "Teams", icon: '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" stroke="currentColor" stroke-width="2" fill="none"/>' },
  { view: "spieler", href: "#spieler", label: "Spieler", icon: '<circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2" fill="none"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6" stroke="currentColor" stroke-width="2" fill="none"/>' },
  { view: "scouting", href: "#scouting", label: "Scouting", icon: '<circle cx="11" cy="11" r="6" stroke="currentColor" stroke-width="2" fill="none"/><path d="M16 16l5 5" stroke="currentColor" stroke-width="2"/>' },
];

const tabOf = (r: Route): string => (r.view === "spiel" || r.view === "prognose" ? "spiele" : r.view === "team" || r.view === "rang" ? "teams" : r.view === "status" ? "verein" : r.view);

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
  if (route.view === "verein") {
    header("Mein Verein", "Matchplan");
    if (route.change) writeFav(null);
    if (route.key) {
      writeFav(route.key);
      history.replaceState(null, "", "#verein");
    }
    if (!season) return NO_DATA;
    const fav = readFav();
    if (!fav) return renderVerein(null, season, null, null, null);
    const mine = await loadJson<ScoutReport>(`scouting/${fav}.json`);
    const n = mine?.next;
    const oppKey = n ? (n.home === fav ? n.away : n.home) : null;
    const [opp, ts] = await Promise.all([oppKey ? loadJson<ScoutReport>(`scouting/${oppKey}.json`) : Promise.resolve(null), loadJson<TeamStats>("teamstats.json")]);
    header(season.teams[fav]?.short ?? "Mein Verein", "Mein Verein");
    return renderVerein(fav, season, mine, opp, ts);
  }
  if (route.view === "scouting") {
    if (!season) {
      header("Scouting", "Matchplan");
      return NO_DATA;
    }
    if (!route.key) {
      header("Scouting", "Gegner-Bericht über jedes Team");
      return renderScoutPicker(season, "#scouting/");
    }
    const fav = readFav();
    const [rep, mine, refs] = await Promise.all([loadJson<ScoutReport>(`scouting/${route.key}.json`), fav && fav !== route.key ? loadJson<ScoutReport>(`scouting/${fav}.json`) : Promise.resolve(null), loadJson<Referees>("referees.json")]);
    header(season.teams[route.key]?.short ?? route.key, "Gegner-Bericht", "#scouting");
    return rep ? renderReport(rep, season, mine, route.section, refs) : NO_DATA;
  }
  if (route.view === "spieler") {
    if (!season) {
      header("Spieler", "Matchplan");
      return NO_DATA;
    }
    const idx = await loadJson<PlayerIndex>("players.json");
    if (route.id) {
      const row = idx?.players.find((r) => r.id === route.id) ?? null;
      header(row?.name ?? "Spieler", "Spielerprofil", "#spieler");
      const [prof, sim] = await Promise.all([loadJson<PlayerProfile>(`players/${route.id}.json`), loadJson<SimilarFile>("similar.json")]);
      return renderPlayer(prof, row, season, sim?.players[String(route.id)] ?? (prof ? sim?.players[String(prof.id)] : undefined) ?? null);
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
    const refs = !match.finished ? await loadJson<Referees>("referees.json") : null;
    return renderMatch(match, season, fitting, history, fm, pred, refs);
  }

  if (route.view === "rang") {
    const ts = await loadJson<TeamStats>("teamstats.json");
    const label = ts?.metrics.find((m) => m.key === route.metric)?.label ?? "Rangliste";
    header(label, "Rangliste aller Teams", `#team/${route.key}`);
    return (ts && renderMetricRanking(route.metric, route.key, ts, season)) || NO_DATA;
  }

  const table = await loadJson<Table>("table.json");
  if (route.view === "teams") {
    header("Tabelle", "1. Bundesliga · Saison 26/27");
    return table ? renderTable(table.rows, season) : NO_DATA;
  }

  const t = season.teams[route.key];
  header(t?.short ?? route.key, "Teamprofil", "#teams");
  if (!t) return NO_DATA;
  const [mds, lineups, ts, idx, model] = await Promise.all([allMatchdays(), loadJson<Lineups>("lineups/current.json"), loadJson<TeamStats>("teamstats.json"), loadJson<PlayerIndex>("players.json"), loadJson<ModelCheck>("model.json")]);
  return renderTeam(route.key, season, table?.rows ?? [], mds.flatMap((d) => d.matches), lineups, (ts ? renderTeamStats(route.key, ts) : "") + (idx ? renderSquad(idx.players, route.key) : ""), model?.elo?.[route.key] ?? null);
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
    if (route.view === "scouting" && route.section) document.getElementById(`area-${route.section}`)?.scrollIntoView();
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
  if (!(route.view === "scouting" && route.section)) window.scrollTo(0, 0);
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => undefined);
window.addEventListener("hashchange", () => void render());
void render();

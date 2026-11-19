import type { FotmobMatch, Match, Season, StatValue, TeamInfo } from "../data";
import { esc } from "../ui";

const info = (s: Season, k: string): TeamInfo => s.teams[k] ?? { name: k, short: k, color: "#64748b", crest: "" };

export const ratingColor = (r: number): string => (r >= 8 ? "#2f6fe4" : r >= 7 ? "#13a150" : r >= 6.5 ? "#f08a00" : "#e5484d");
const ratingChip = (r: number | null): string =>
  r == null ? "" : `<span class="rt" style="background:${ratingColor(r)}">${r.toFixed(1).replace(".", ",")}</span>`;

const de = (x: number, digits: number): string => x.toFixed(digits).replace(".", ",");
const num = (v: StatValue): number => (v == null ? 0 : typeof v === "number" ? v : v.n);

type Row = [key: string, label: string, kind?: "pct" | "xg" | "low"];
const GROUPS: [string, Row[]][] = [
  ["Überblick", [["BallPossesion", "Ballbesitz", "pct"], ["expected_goals", "xG", "xg"], ["total_shots", "Schüsse"], ["ShotsOnTarget", "Aufs Tor"], ["big_chance", "Großchancen"], ["touches_opp_box", "Ballaktionen im gegn. Strafraum"]]],
  ["xG", [["expected_goals_open_play", "xG aus dem Spiel", "xg"], ["expected_goals_set_play", "xG nach Standards", "xg"], ["expected_goals_on_target", "xGOT", "xg"]]],
  ["Schüsse", [["total_shots", "Schüsse gesamt"], ["ShotsOnTarget", "Aufs Tor"], ["shots_inside_box", "Aus dem Strafraum"], ["blocked_shots", "Geblockt"], ["big_chance_missed_title", "Großchancen vergeben", "low"]]],
  ["Passspiel & Aufbau", [["passes", "Pässe"], ["accurate_passes", "Angekommen"], ["opposition_half_passes", "In der gegn. Hälfte"], ["long_balls_accurate", "Lange Bälle angekommen"], ["accurate_crosses", "Flanken angekommen"], ["corners", "Ecken"], ["Offsides", "Abseits", "low"]]],
  ["Defensive", [["tackles", "Tacklings"], ["interceptions", "Abgefangene Bälle"], ["shot_blocks", "Geblockte Schüsse"], ["clearances", "Klärungen"], ["keeper_saves", "Paraden"]]],
  ["Zweikämpfe", [["duel_won", "Zweikämpfe gewonnen"], ["ground_duels_won", "Am Boden"], ["aerials_won", "In der Luft"], ["dribbles_succeeded", "Dribblings erfolgreich"]]],
  ["Disziplin", [["fouls", "Fouls", "low"], ["yellow_cards", "Gelbe Karten", "low"], ["red_cards", "Rote Karten", "low"]]],
];

const show = (v: StatValue, kind?: string): string => {
  if (v == null) return "–";
  if (typeof v !== "number") return `${v.n} (${v.pct} %)`;
  if (kind === "pct") return `${v} %`;
  if (kind === "xg") return de(v, 2);
  return String(v);
};

function statRows(fm: FotmobMatch, h: TeamInfo, a: TeamInfo): string {
  return GROUPS.map(([title, rows], i) => {
    const body = rows
      .filter(([k]) => fm.stats[k])
      .map(([k, label, kind]) => {
        const [hv, av] = fm.stats[k];
        const x = num(hv), y = num(av), t = x + y || 1;
        const low = kind === "low";
        const hw = low ? x < y : x > y, aw = low ? y < x : y > x;
        return `<div class="vs"><span class="l">${esc(show(hv, kind))}</span><span class="lab">${esc(label)}</span><span class="r">${esc(show(av, kind))}</span>
          <div class="bb"><i class="${hw ? "w" : ""}" style="flex:${x / t};background:${esc(h.color)}"></i><i class="${aw ? "w" : ""}" style="flex:${y / t};background:${esc(a.color)}"></i></div></div>`;
      })
      .join("");
    return body ? `<details class="cat" ${i < 2 ? "open" : ""}><summary><b>${esc(title)}</b></summary><div class="catbody">${body}</div></details>` : "";
  }).join("");
}

function momentum(fm: FotmobMatch, m: Match, h: TeamInfo, a: TeamInfo): string {
  const data = fm.momentum!;
  const last = Math.ceil(Math.max(90, ...data.map((p) => p[0])));
  const X = (min: number) => 8 + (min / last) * 284;
  const Y = (v: number) => 60 - (v / 100) * 50;
  const d = data.map(([mi, v], i) => `${i ? "L" : "M"}${X(mi).toFixed(1)} ${Y(v).toFixed(1)}`).join(" ");
  const area = `${d} L${X(data[data.length - 1][0]).toFixed(1)} 60 L${X(data[0][0]).toFixed(1)} 60 Z`;
  const goals = m.goals
    .filter((g) => g.minute != null)
    .map((g) => `<circle cx="${X(g.minute!).toFixed(1)}" cy="${g.team === m.home ? 8 : 112}" r="5" fill="var(--surface)" stroke="${esc(g.team === m.home ? h.color : a.color)}" stroke-width="2.5"/>`)
    .join("");
  return `<section class="card"><h3>Momentum</h3>
    <svg viewBox="0 0 300 130" width="100%" role="img" aria-label="Spielverlauf">
      <defs><clipPath id="mu"><rect x="0" y="0" width="300" height="60"/></clipPath><clipPath id="md"><rect x="0" y="60" width="300" height="70"/></clipPath></defs>
      <path class="mom" d="${area}" fill="${esc(h.color)}" clip-path="url(#mu)" fill-opacity=".85"/>
      <path d="${area}" fill="${esc(a.color)}" clip-path="url(#md)" fill-opacity=".85"/>
      <line x1="8" y1="60" x2="292" y2="60" stroke="var(--muted)"/>${goals}
      <text x="8" y="126" font-size="9" fill="var(--muted)">0'</text><text x="292" y="126" font-size="9" fill="var(--muted)" text-anchor="end">${last}'</text>
    </svg><p class="muted">Ausschlag nach oben: ${esc(h.short)} drückt, nach unten: ${esc(a.short)}. Kreise = Tore. Quelle: FotMob</p></section>`;
}

function shotmap(fm: FotmobMatch, m: Match, h: TeamInfo, a: TeamInfo): string {
  const W = 105, H = 68;
  const dots = fm.shots
    .filter((s) => s.x != null && s.y != null && s.team)
    .map((s) => {
      const home = s.team === m.home;
      const x = home ? s.x! : W - s.x!;
      const y = home ? s.y! : H - s.y!;
      const r = 1 + (s.xg ?? 0) * 6;
      const goal = s.result === "goal";
      const col = home ? h.color : a.color;
      const fill = goal ? "#ffc14d" : home ? esc(col) : "#fff";
      const stroke = home ? "#fff" : esc(col);
      return `<circle class="shot${goal ? " goal" : ""}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(2)}" fill="${fill}" fill-opacity="${goal ? 1 : home ? 0.6 : 0.85}" stroke="${stroke}" stroke-width="${home ? 0.35 : 0.6}"><title>${esc(s.player ?? "")} ${s.min ?? ""}' · xG ${de(s.xg ?? 0, 2)}</title></circle>`;
    })
    .join("");
  const lines = `<g fill="none" stroke="#fff" stroke-opacity=".5" stroke-width=".4"><rect x="0.5" y="0.5" width="104" height="67"/><line x1="52.5" y1="0.5" x2="52.5" y2="67.5"/><circle cx="52.5" cy="34" r="9.15"/><rect x="0.5" y="13.85" width="16.5" height="40.3"/><rect x="88" y="13.85" width="16.5" height="40.3"/></g>`;
  const sum = (k: string) => de(fm.shots.filter((s) => s.team === k && !s.own_goal).reduce((t, s) => t + (s.xg ?? 0), 0), 2);
  return `<section class="card"><h3>Schusskarte</h3>
    <div class="pitchwrap"><svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Schusskarte">${lines}${dots}</svg></div>
    <p class="muted">${esc(h.short)} (ausgefüllt) greift nach rechts an, ${esc(a.short)} (weiß) nach links. Kreisgröße = xG, gelb = Tor. xG aus allen Schüssen: ${esc(h.short)} ${sum(m.home)}, ${esc(a.short)} ${sum(m.away)}.</p></section>`;
}

function zones(fm: FotmobMatch, h: TeamInfo, a: TeamInfo): string {
  const row = (t: TeamInfo, z: Record<string, number>) =>
    `<div class="row" style="gap:6px"><b style="width:84px">${esc(t.short)}</b>${(["left", "center", "right"] as const)
      .map((k) => `<span class="zone" style="background:color-mix(in srgb,${esc(t.color)} ${Math.round(20 + z[k])}%,var(--surface2))">${z[k]} %</span>`)
      .join("")}</div>`;
  return `<section class="card"><h3>Angriffszonen</h3><div class="row muted" style="gap:6px"><span style="width:84px"></span><span class="zone">links</span><span class="zone">Mitte</span><span class="zone">rechts</span></div>
    ${row(h, fm.zones!.home)}${row(a, fm.zones!.away)}<p class="muted">Anteil der Angriffe über die jeweilige Seite, aus Sicht des angreifenden Teams.</p></section>`;
}

function lineups(fm: FotmobMatch, h: TeamInfo, a: TeamInfo): string {
  const lu = fm.lineups!;
  const list = (t: TeamInfo, l: typeof lu.home) =>
    `<div class="col"><b>${esc(t.short)}</b><div class="row" style="gap:6px"><span class="chip">${esc(l.formation ?? "")}</span>${ratingChip(l.rating)}</div>
      ${l.players.map((p) => `<div class="row pl">${ratingChip(p.rating)}${p.id ? `<a href="#spieler/${p.id}">${esc(p.name)}${p.captain ? " (C)" : ""}</a>` : `<span>${esc(p.name)}${p.captain ? " (C)" : ""}</span>`}</div>`).join("")}</div>`;
  const all = [...lu.home.players.map((p) => ({ ...p, t: h })), ...lu.away.players.map((p) => ({ ...p, t: a }))]
    .filter((p) => p.rating != null)
    .sort((x, y) => y.rating! - x.rating!)
    .slice(0, 3);
  return `<section class="card"><h3>Aufstellungen & Noten</h3>
    ${all.length ? `<div class="row" style="flex-wrap:wrap;gap:8px"><span class="muted">Beste Spieler:</span>${all.map((p) => `<span class="row" style="gap:4px">${ratingChip(p.rating)}${p.id ? `<a href="#spieler/${p.id}">${esc(p.name)}</a>` : esc(p.name)}</span>`).join("")}</div>` : ""}
    <div class="two">${list(h, lu.home)}${list(a, lu.away)}</div><p class="muted">Note von 0 bis 10 (FotMob).</p></section>`;
}

export function renderAnalysis(m: Match, fm: FotmobMatch | null, season: Season): string {
  if (!fm) return `<section class="card"><p class="muted">Noch keine Spielstatistik für dieses Spiel. Sie wird nach dem Spiel automatisch geladen.</p></section>`;
  const h = info(season, m.home), a = info(season, m.away);
  return [
    fm.momentum?.length ? momentum(fm, m, h, a) : "",
    `<section class="card"><h3>Statistik</h3>${statRows(fm, h, a)}<p class="muted">Quelle: FotMob</p></section>`,
    fm.shots.length ? shotmap(fm, m, h, a) : "",
    fm.zones ? zones(fm, h, a) : "",
    fm.lineups ? lineups(fm, h, a) : "",
  ].join("");
}

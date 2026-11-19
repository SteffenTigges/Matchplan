import type { Lineups, Match, Season, TableRow, TeamInfo } from "../data";
import { berlin, crest, esc } from "../ui";
import { renderMissing, renderTeamPitch } from "./lineup";

const info = (s: Season, key: string): TeamInfo => s.teams[key] ?? { name: key, short: key, color: "#64748b", crest: "" };
const form = (f: string[]): string => `<span class="form">${f.map((x) => `<i class="${esc(x)}">${esc(x)}</i>`).join("")}</span>`;

export function renderTable(rows: TableRow[], season: Season): string {
  const items = [...rows]
    .sort((a, b) => a.rank - b.rank)
    .map((r) => {
      const t = info(season, r.team);
      return `<a class="item" href="#team/${esc(r.team)}"><span class="num muted" style="width:18px">${r.rank}</span>${crest(t, 26)}
        <span class="grow"><b>${esc(t.short)}</b><br>${form(r.form)}</span>
        <span class="muted num" style="text-align:right">${r.played} Sp.<br>${r.diff > 0 ? "+" : ""}${r.diff}</span>
        <span class="num" style="font-weight:700;width:28px;text-align:right">${r.points}</span></a>`;
    })
    .join("");
  return `<div class="list">${items}</div>`;
}

const result = (m: Match, key: string): string => {
  if (!m.score) return "";
  const [h, a] = m.score;
  const mine = m.home === key ? h - a : a - h;
  return `<span class="form"><i class="${mine > 0 ? "S" : mine === 0 ? "U" : "N"}">${mine > 0 ? "S" : mine === 0 ? "U" : "N"}</i></span>`;
};

export function renderTeam(key: string, season: Season, rows: TableRow[], matches: Match[], lineups: Lineups | null, statsHtml = ""): string {
  const t = info(season, key);
  const row = rows.find((r) => r.team === key);
  const mine = matches.filter((m) => m.home === key || m.away === key).sort((a, b) => (a.kickoff ?? "9").localeCompare(b.kickoff ?? "9"));
  const next = mine.find((m) => !m.finished);
  const played = mine.filter((m) => m.finished && m.score).reverse();

  const hero = `<div class="hero" style="background:linear-gradient(135deg,${esc(t.color)} 0%,color-mix(in srgb,${esc(t.color)} 55%,#000) 100%)">
    <div class="row">${crest(t, 52)}<div><div class="tlab">${row ? `${row.rank}. Platz · ${row.points} Punkte` : ""}</div><h2 style="color:#fff">${esc(t.name)}</h2></div></div>
    ${row ? `<div>${form(row.form)}</div>` : ""}</div>`;

  const nextCard = next
    ? (() => {
        const opp = info(season, next.home === key ? next.away : next.home);
        return `<a class="card" href="#spiel/${next.id}"><div class="row" style="justify-content:space-between"><span class="tlab">Nächstes Spiel · ${next.kickoff ? esc(berlin(next.kickoff)) : "Termin offen"} · ${next.home === key ? "zu Hause" : "auswärts"}</span><span class="chev">›</span></div>
          <div class="row">${crest(opp, 30)}<b>${esc(opp.name)}</b></div></a>`;
      })()
    : "";

  const lu = lineups?.teams[key];
  const lineupCard = lu
    ? `<section class="card"><h2>Voraussichtliche Aufstellung</h2><span class="chip" style="align-self:flex-start">${esc(lu.formation)}</span>
        ${renderTeamPitch(lu, t)}
        <p class="muted">Quelle: Ligainsider · Stand ${esc(berlin(lu.fetched_at))} Uhr</p></section>
      <section class="card"><h2>Es fehlen</h2>${renderMissing(t, lu)}</section>`
    : "";

  const results = played.length
    ? `<section class="card"><h3>Ergebnisse</h3><div class="list">${played
        .map((m) => {
          const opp = info(season, m.home === key ? m.away : m.home);
          return `<a class="item" href="#spiel/${m.id}">${result(m, key)}${crest(opp, 22)}<span class="grow">${m.home === key ? "gegen" : "bei"} ${esc(opp.short)}</span><span class="num" style="font-weight:700">${m.score![0]}:${m.score![1]}</span></a>`;
        })
        .join("")}</div></section>`
    : "";

  return hero + nextCard + statsHtml + lineupCard + results;
}

import type { History, Lineups, Match, Season, TeamInfo } from "../data";
import { berlin, crest, esc } from "../ui";
import { renderHistory, renderMissing, renderPitch } from "./lineup";

const team = (s: Season, key: string): TeamInfo => s.teams[key] ?? { name: key, short: key, color: "#64748b", crest: "" };

const middle = (m: Match): string =>
  m.finished && m.score
    ? `<div class="score">${m.score[0]}:${m.score[1]}</div>`
    : m.kickoff
      ? `<div class="tlab">Anstoß</div><div class="big num">${esc(berlin(m.kickoff).split(", ")[1])}</div>`
      : `<div class="tlab">Termin offen</div>`;

const status = (m: Match): string =>
  m.finished ? "Beendet" : m.kickoff ? esc(berlin(m.kickoff)) : "Termin offen";

export function renderMatchday(md: number, matches: Match[], season: Season): string {
  const prev = md > 1 ? `<a href="#spiele/${md - 1}">‹ ${md - 1}.</a>` : `<a aria-disabled="true">‹</a>`;
  const next = md < 34 ? `<a href="#spiele/${md + 1}">${md + 1}. ›</a>` : `<a aria-disabled="true">›</a>`;
  const sorted = [...matches].sort((a, b) => (a.kickoff ?? "9").localeCompare(b.kickoff ?? "9"));
  const cards = sorted
    .map((m) => {
      const h = team(season, m.home);
      const a = team(season, m.away);
      return `<a class="card" href="#spiel/${m.id}">
        <div class="row" style="justify-content:space-between"><span class="tlab">${status(m)}</span><span class="chev">›</span></div>
        <div class="fx"><div class="t">${crest(h, 34)}<span>${esc(h.short)}</span></div><div class="mid">${middle(m)}</div><div class="t">${crest(a, 34)}<span>${esc(a.short)}</span></div></div>
      </a>`;
    })
    .join("");
  return `<div class="pager">${prev}<b>${md}. Spieltag</b>${next}</div>${cards || `<section class="card"><p class="muted">Für diesen Spieltag sind noch keine Spiele angesetzt.</p></section>`}`;
}

export function renderMatch(m: Match, season: Season, lineups: Lineups | null, history: History | null): string {
  const h = team(season, m.home);
  const a = team(season, m.away);
  const hero = `<div class="hero" style="background:linear-gradient(120deg,${esc(h.color)} 0%,color-mix(in srgb,${esc(h.color)} 40%,#111) 48%,color-mix(in srgb,${esc(a.color)} 40%,#111) 52%,${esc(a.color)} 100%)">
    <div class="fx"><div class="t">${crest(h, 44)}<span>${esc(h.short)}</span></div><div class="mid">${m.finished && m.score ? `<div class="tlab">Endstand</div><div class="score" style="font-size:48px">${m.score[0]}:${m.score[1]}</div>${m.halftime ? `<div class="tlab">Halbzeit ${m.halftime[0]}:${m.halftime[1]}</div>` : ""}` : `<div class="tlab">${status(m)}</div>`}</div><div class="t">${crest(a, 44)}<span>${esc(a.short)}</span></div></div></div>`;

  if (m.finished) {
    const goals = m.goals.length
      ? `<ul class="goals">${m.goals
          .map((g) => {
            const t = team(season, g.team);
            const tag = g.penalty ? ' <span class="chip">Elfmeter</span>' : g.own_goal ? ' <span class="chip bad">Eigentor</span>' : "";
            return `<li><span class="num">${g.minute ?? "–"}'</span><span><b>${esc(g.scorer)}</b>${tag}</span>${crest(t, 18)}</li>`;
          })
          .join("")}</ul>`
      : `<p class="muted">Keine Tore</p>`;
    return `${hero}<section class="card"><h3>Tore</h3>${goals}</section>`;
  }

  const hl = lineups?.teams[m.home];
  const al = lineups?.teams[m.away];
  if (!hl || !al || lineups?.matchday === undefined) {
    return `${hero}<section class="card"><h2>Voraussichtliche Aufstellung</h2><p class="muted">Noch keine voraussichtliche Aufstellung für dieses Spiel.</p></section>`;
  }
  const events = (history?.events ?? []).filter((e) => e.team === m.home || e.team === m.away);
  return `${hero}
    <section class="card"><h2>Voraussichtliche Aufstellung</h2>
      <div class="row" style="justify-content:space-between"><span class="chip">${esc(a.short)} · ${esc(al.formation)}</span><span class="chip">${esc(h.short)} · ${esc(hl.formation)}</span></div>
      ${renderPitch(hl, al, h, a)}
      <p class="muted">Unten ${esc(h.short)}, oben ${esc(a.short)}. Gelb „oder …“: Ligainsider hält die Position für offen und nennt die Alternative.</p>
      <p class="muted">Quelle: Ligainsider · Stand ${esc(berlin(hl.fetched_at))} Uhr</p></section>
    <section class="card"><h2>Es fehlen</h2>${renderMissing(h, hl)}${renderMissing(a, al)}</section>
    <section class="card"><h2>Verlauf der Woche</h2>${renderHistory(events, season.teams)}</section>`;
}

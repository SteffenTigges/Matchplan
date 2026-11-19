import type { ScoutReport, Season, TeamInfo, TeamStats } from "../data";
import { berlin, crest, esc } from "../ui";
import { AREAS, findingList, renderScoutPicker } from "./scouting";
import { formatMetric } from "./teamstats";

const KEY = "matchplan.verein";
const team = (s: Season, key: string): TeamInfo => s.teams[key] ?? { name: key, short: key, color: "#64748b", crest: "" };
const pct = (x: number): string => `${Math.round(x * 100)} %`;

/** Lieblingsverein steht nur im Browser dieses Geräts; ohne Speicher fragt die Seite einfach erneut. */
export function readFav(store: Storage | null = typeof localStorage !== "undefined" ? localStorage : null): string | null {
  try {
    const v = store?.getItem(KEY) ?? null;
    return v && /^[A-Z0-9]{3}$/.test(v) ? v : null;
  } catch {
    return null;
  }
}

export function writeFav(key: string | null, store: Storage | null = typeof localStorage !== "undefined" ? localStorage : null): void {
  try {
    if (key) store?.setItem(KEY, key);
    else store?.removeItem(KEY);
  } catch {
    /* Speicher gesperrt: dann eben nur für diesen Besuch */
  }
}

const VS = ["goals_pg", "xg_pg", "big_chances_pg", "against_pg", "xga_pg", "possession", "field_tilt", "ppda", "xg_setplay_pg", "duel_rate"];

function wirGegenSie(me: string, them: string, ts: TeamStats, season: Season): string {
  const a = team(season, me);
  const b = team(season, them);
  const rows = VS.map((k) => {
    const m = ts.metrics.find((x) => x.key === k);
    const l = ts.teams[me]?.[k];
    const r = ts.teams[them]?.[k];
    if (!m || !l || !r || typeof l === "number" || typeof r === "number" || l.value == null || r.value == null) return "";
    const lw = m.higher_is_better ? l.value >= r.value : l.value <= r.value;
    const lv = Math.abs(l.value);
    const rv = Math.abs(r.value);
    const tot = lv + rv || 1;
    return `<span class="l">${esc(formatMetric(l.value, m.fmt))}<br><span class="muted">${l.rank}.</span></span><span class="lab">${esc(m.label)}</span><span class="r">${esc(formatMetric(r.value, m.fmt))}<br><span class="muted">${r.rank}.</span></span>
      <span class="bb"><i class="${lw ? "w" : ""}" style="flex:${lv / tot};background:${esc(a.color)}"></i><i class="${!lw ? "w" : ""}" style="flex:${rv / tot};background:${esc(b.color)}"></i></span>`;
  }).join("");
  if (!rows) return "";
  return `<section class="card"><h2>Wir gegen sie</h2><div class="row" style="justify-content:space-between">${crest(a, 24)}<span class="muted">Saisonwerte · Ligaplatz</span>${crest(b, 24)}</div><div class="vs">${rows}</div></section>`;
}

export function renderVerein(fav: string | null, season: Season, mine: ScoutReport | null, opp: ScoutReport | null, ts: TeamStats | null): string {
  if (!fav || !season.teams[fav]) {
    return `<section class="card"><h2>Mein Verein</h2><p class="muted">Wähle deinen Verein. Die Auswahl bleibt nur auf diesem Gerät gespeichert.</p></section>${renderScoutPicker(season, "#verein/", "Verein wählen")}`;
  }
  const me = team(season, fav);
  const n = mine?.next ?? null;
  const oppKey = n ? (n.home === fav ? n.away : n.home) : null;
  const o = oppKey ? team(season, oppKey) : null;

  const hero = `<div class="hero" style="background:linear-gradient(135deg,${esc(me.color)} 0%,color-mix(in srgb,${esc(me.color)} 55%,#000) 100%)">
    <div class="row">${crest(me, 52)}<div><div class="tlab">Mein Verein</div><h2 style="color:#fff">${esc(me.name)}</h2></div></div></div>`;

  const next = n && o
    ? `<a class="card" href="#spiel/${n.id}"><div class="row" style="justify-content:space-between"><span class="tlab">Nächstes Spiel · ${n.kickoff ? esc(berlin(n.kickoff)) : "Termin offen"} · ${n.home === fav ? "zu Hause" : "auswärts"}</span><span class="chev">›</span></div>
        <div class="row">${crest(o, 34)}<span class="grow"><b>${n.home === fav ? "gegen" : "bei"} ${esc(o.name)}</b></span>${n.tip ? `<span class="chip">Tipp ${n.home === fav ? `${n.tip[0]}:${n.tip[1]}` : `${n.tip[1]}:${n.tip[0]}`}</span>` : ""}</div>
        ${n.probs ? `<div class="kpis"><div class="kpi"><span class="tlab">Sieg</span><b>${pct(n.home === fav ? n.probs[0] : n.probs[2])}</b></div><div class="kpi"><span class="tlab">Remis</span><b>${pct(n.probs[1])}</b></div><div class="kpi"><span class="tlab">Niederlage</span><b>${pct(n.home === fav ? n.probs[2] : n.probs[0])}</b></div></div>` : ""}</a>`
    : `<section class="card"><p class="muted">Kein weiteres Spiel angesetzt.</p></section>`;

  const findings = opp && o
    ? `<section class="card"><h2>Die 3 wichtigsten Erkenntnisse über ${esc(o.short)}</h2>${findingList(opp.findings, "Noch zu wenige Daten über diesen Gegner.")}</section>
       <section class="card"><h2>Gegner-Bericht ${esc(o.short)}</h2><div class="tiles">${AREAS.map((a) => `<a href="#scouting/${esc(oppKey!)}/${a.id}">${esc(a.title)}<span class="chev">›</span></a>`).join("")}</div></section>`
    : "";

  const vs = ts && oppKey ? wirGegenSie(fav, oppKey, ts, season) : "";
  const links = `<section class="card"><div class="tiles"><a href="#scouting/${esc(fav)}">Eigener Bericht<span class="chev">›</span></a><a href="#team/${esc(fav)}">Teamprofil<span class="chev">›</span></a><a href="#status">Datenquellen<span class="chev">›</span></a><a href="#verein/wechseln">Verein wechseln<span class="chev">›</span></a></div></section>`;
  return hero + next + findings + vs + links;
}

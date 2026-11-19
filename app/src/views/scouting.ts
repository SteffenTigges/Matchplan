import type { Evidence, Finding, ScoutReport, Season, Situations, TeamInfo, Zones } from "../data";
import { berlin, crest, esc, photo } from "../ui";
import { ratingColor } from "./analysis";
import { fotmobPhoto } from "./players";
import { formatMetric } from "./teamstats";

const team = (s: Season, key: string): TeamInfo => s.teams[key] ?? { name: key, short: key, color: "#64748b", crest: "" };
const pct = (x: number): string => `${Math.round(x * 100)} %`;
const dec = (x: number, n = 2): string => x.toFixed(n).replace(".", ",");
const none = (what: string): string => `<p class="muted">${esc(what)}</p>`;

export const AREAS: { id: string; title: string }[] = [
  { id: "ueberblick", title: "Überblick" },
  { id: "mitball", title: "Mit Ball" },
  { id: "gegendenball", title: "Gegen den Ball" },
  { id: "personal", title: "Personal" },
  { id: "verlauf", title: "Spielverlauf" },
];

/** Ein Beleg: Kennzahl, Wert, Ligaplatz. */
export function evidence(e: Evidence): string {
  return `<span class="ev"><span>${esc(e.label)}</span><b class="num">${esc(formatMetric(e.value, e.fmt))}</b>${e.rank != null ? `<span class="muted">Platz ${e.rank}</span>` : ""}</span>`;
}

export function findingList(items: Finding[], empty: string): string {
  if (!items.length) return none(empty);
  return `<ol class="findings">${items.map((f) => `<li><b>${esc(f.text)}</b><div class="evs">${f.evidence.map(evidence).join("")}</div></li>`).join("")}</ol>`;
}

const evRows = (list: Evidence[]): string => (list.length ? `<div class="evs">${list.map(evidence).join("")}</div>` : "");

function situations(s: Situations | null, color: string): string {
  if (!s) return none("Keine Schussdaten vorhanden.");
  const rows = (Object.keys(s) as (keyof Situations)[])
    .map((k) => `<div class="srow"><span>${esc(k)}</span><span class="num">${s[k].goals} Tore · ${dec(s[k].xg, 1)} xG</span><span class="num" style="width:44px;text-align:right">${pct(s[k].share)}</span></div>
      <span class="pbar"><i style="width:${s[k].share * 100}%;background:${esc(color)}"></i></span>`)
    .join("");
  return `<div class="catbody">${rows}</div>`;
}

const BANDS = ["1–15", "16–30", "31–45", "46–60", "61–75", "76–90"];
function bands(b: number[], color: string, label: string): string {
  const max = Math.max(1, ...b);
  return `<div class="tlab">${esc(label)} nach Spielminute</div><div class="bands">${b
    .map((n, i) => `<div><span class="bar" style="height:${8 + (n / max) * 56}px;background:${esc(color)}"></span><b class="num">${n}</b><span class="muted">${BANDS[i]}</span></div>`)
    .join("")}</div>`;
}

function zones(z: Zones | null, label: string, color: string): string {
  if (!z) return "";
  return `<div class="tlab">${esc(label)}</div><div class="row" style="gap:4px">${(["left", "center", "right"] as const)
    .map((k) => `<span class="zone" style="background:color-mix(in srgb,${esc(color)} ${Math.round(z[k] * 1.4)}%,var(--surface2))">${k === "left" ? "links" : k === "center" ? "Mitte" : "rechts"} ${Math.round(z[k])} %</span>`)
    .join("")}</div>`;
}

const section = (id: string, title: string, body: string): string => `<div class="sec" id="sec-${id}"><h3>${esc(title)}</h3>${body}</div>`;

function duels(r: ScoutReport, mine: ScoutReport, season: Season): string {
  const me = team(season, mine.team);
  const them = team(season, r.team);
  const rows = (["Abwehr", "Mittelfeld", "Angriff"] as const)
    .map((line) => {
      // Unser Angriff gegen ihre Abwehr usw.
      const opp = line === "Angriff" ? "Abwehr" : line === "Abwehr" ? "Angriff" : "Mittelfeld";
      const a = mine.lines[line];
      const b = r.lines[opp];
      if (!a && !b) return "";
      const cell = (p: { id: number; name: string; rating: number } | undefined, t: TeamInfo): string =>
        p ? `<a class="row" href="#spieler/${p.id}" style="gap:6px;color:inherit;text-decoration:none;min-width:0">${photo(fotmobPhoto(p.id), p.name, 30)}<span style="min-width:0"><b>${esc(p.name)}</b><br><span class="rt" style="background:${ratingColor(p.rating)}">${dec(p.rating, 1)}</span></span></a>` : `<span class="muted">–</span>`;
      return `<div class="duel"><span class="tlab">Unser ${line} gegen ihr${opp === "Abwehr" ? "e" : ""} ${opp}</span><div class="two"><div class="col">${cell(a, me)}</div><div class="col">${cell(b, them)}</div></div></div>`;
    })
    .join("");
  return section("duelle", "Duelle", rows || none("Noch zu wenige Einsatzminuten für einen Vergleich."));
}

export function renderReport(r: ScoutReport, season: Season, mine: ScoutReport | null, open?: string): string {
  const t = team(season, r.team);
  const nav = `<div class="seg">${AREAS.map((a) => `<a href="#scouting/${esc(r.team)}/${a.id}">${esc(a.title)}</a>`).join("")}</div>`;
  const hero = `<div class="hero" style="background:linear-gradient(135deg,${esc(t.color)} 0%,color-mix(in srgb,${esc(t.color)} 55%,#000) 100%)">
    <div class="row">${crest(t, 48)}<div><div class="tlab">Gegner-Bericht · ${r.matches} Spiele</div><h2 style="color:#fff">${esc(t.name)}</h2></div></div>
    <div class="pills">${r.idea.formations.slice(0, 2).map((f) => `<span class="pill">${esc(f.formation)} · ${f.games}×</span>`).join("")}${r.idea.tags.map((x) => `<span class="pill">${esc(x.text)}</span>`).join("")}</div></div>`;

  const n = r.next;
  const nextHtml = n
    ? (() => {
        const h = team(season, n.home);
        const a = team(season, n.away);
        return `<a class="item" href="#spiel/${n.id}" style="padding:8px 0">${crest(h, 24)}<span class="grow"><b>${esc(h.short)} – ${esc(a.short)}</b><br><span class="muted">${n.kickoff ? esc(berlin(n.kickoff)) : "Termin offen"}</span></span>${n.tip ? `<span class="chip">Tipp ${n.tip[0]}:${n.tip[1]}</span>` : ""}${crest(a, 24)}</a>`;
      })()
    : none("Kein weiteres Spiel angesetzt.");

  const formations = r.idea.formations.length
    ? `<div class="row" style="flex-wrap:wrap;gap:6px">${r.idea.formations.map((f) => `<span class="chip">${esc(f.formation)} · ${f.games} Spiele</span>`).join("")}</div>`
    : none("Keine Aufstellungsdaten.");

  const area = (id: string, title: string, body: string): string =>
    `<details class="card area" id="area-${id}" ${!open || open === id ? "open" : ""}><summary><h2>${esc(title)}</h2></summary>${body}</details>`;

  const ueberblick = area("ueberblick", "Überblick",
    section("idee", "Spielidee", formations + (r.idea.tags.length ? findingList(r.idea.tags, "") : none("Kein auffälliges Muster in den Kennzahlen."))) +
    section("prognose", "Prognose", nextHtml) +
    section("staerken", "Stärken & Schwächen", `<div class="tlab">Stärken</div>${r.strengths.length ? evRows(r.strengths) : none("Keine Kennzahl unter den besten drei.")}<div class="tlab">Schwächen</div>${r.weaknesses.length ? evRows(r.weaknesses) : none("Keine Kennzahl unter den schlechtesten drei.")}`) +
    section("matchplan", "Matchplan", findingList(r.matchplan, "Keine eindeutige Schwachstelle in den Zahlen.")));

  const mitball = area("mitball", "Mit Ball",
    section("aufbau", "Spielaufbau", evRows(r.buildup.metrics) + zones(r.buildup.zones, "Angriffsseiten", t.color)) +
    section("treffen", "So treffen sie", situations(r.scoring.situations, t.color) + bands(r.scoring.bands, t.color, `${r.scoring.goals} Tore`) +
      (r.scoring.inside_box != null ? `<p class="muted">${pct(r.scoring.inside_box)} der Schüsse aus dem Strafraum.</p>` : "") + evRows(r.scoring.metrics)));

  const gegen = area("gegendenball", "Gegen den Ball",
    section("kassieren", "So kassieren sie", situations(r.conceding.situations, "#e5484d") + bands(r.conceding.bands, "#e5484d", `${r.conceding.goals} Gegentore`) +
      zones(r.conceding.opp_zones, "Angriffe der Gegner über …", "#e5484d") + evRows(r.conceding.metrics)) +
    section("standards", "Standards", evRows(r.setpieces.metrics) +
      `<p class="muted">Tore nach Standards: ${r.setpieces.goals_for ?? "–"} erzielt, ${r.setpieces.goals_against ?? "–"} kassiert${r.setpieces.corners_against != null ? ` · Ecken des Gegners pro Spiel ${dec(r.setpieces.corners_against, 1)}` : ""}.</p>`));

  const kp = r.key_players.length
    ? `<div class="list">${r.key_players
        .map((p) => `<a class="item" href="#spieler/${p.id}">${photo(fotmobPhoto(p.id), p.name, 40)}<span class="grow"><b>${esc(p.name)}</b>${p.pos ? ` <span class="muted">${esc(p.pos)}</span>` : ""}<br><span class="muted">${p.goals} Tore · ${p.assists} Vorlagen · xG/90 ${dec(p.xg90)} · xA/90 ${dec(p.xa90)}</span>${p.why.length ? `<br><span class="muted">Warum: ${esc(p.why.join(", "))}</span>` : ""}</span>${p.rating != null ? `<span class="rt" style="background:${ratingColor(p.rating)}">${dec(p.rating, 1)}</span>` : ""}</a>`)
        .join("")}</div>`
    : none("Noch kein Spieler mit 450 Minuten.");
  const load = r.load.length
    ? `<div class="tlab">Minuten in den letzten 3 Spielen</div><div class="catbody">${r.load
        .map((p) => `<div class="srow"><span>${esc(p.name)}</span><span class="num">${p.minutes}'</span>${p.full ? '<span class="chip mid">voll belastet</span>' : "<span></span>"}</div>`)
        .join("")}</div>`
    : "";
  const absent = r.absences.length
    ? `<div class="tlab">Es fehlen (Ligainsider)</div><div class="catbody">${r.absences.map((a) => `<div class="srow"><span>${esc(a.name)}</span><span class="muted">${esc(a.note && a.note !== a.name ? a.note : "")}</span><span class="chip bad">${esc(a.kind)}</span></div>`).join("")}</div>`
    : none("Keine Ausfälle gemeldet.");
  const personal = area("personal", "Personal",
    section("schluessel", "Schlüsselspieler", kp) + (mine && mine.team !== r.team ? duels(r, mine, season) : "") + section("belastung", "Personal & Belastung", absent + load));

  const re = r.reaction;
  const ht = (label: string, x: { games: number; points: number }): string =>
    `<div class="kpi"><span class="tlab">${esc(label)}</span><b>${x.games ? dec(x.points / x.games, 1) : "–"}</b><span class="muted">Punkte/Spiel · ${x.games} Spiele</span></div>`;
  const verlauf = area("verlauf", "Spielverlauf",
    section("reaktion", "Reaktion im Spielverlauf", `<div class="tlab">Nach der Halbzeit, je nach Pausenstand</div><div class="kpis">${ht("Führung", re.ht_lead)}${ht("Unentschieden", re.ht_draw)}${ht("Rückstand", re.ht_trail)}</div>
      <p class="muted">Nach Rückstand noch ${re.points_from_behind} Punkte geholt, nach Führung ${re.points_dropped} Punkte abgegeben. Ab der 76. Minute: ${re.late_for} Tore erzielt, ${re.late_against} kassiert.</p>`) +
    section("schiri", "Schiedsrichter", none("Für Schiedsrichter-Daten gibt es keine frei nutzbare Quelle. Dieser Abschnitt bleibt leer.")));

  return hero + nav + ueberblick + mitball + gegen + personal + verlauf + `<p class="muted" style="padding:0 4px">Daten: FotMob (${r.fotmob_matches} Spiele), OpenLigaDB, Ligainsider. Aussagen sind regelbasiert aus den gezeigten Zahlen abgeleitet.</p>`;
}

export function renderScoutPicker(season: Season, base: string, title = "Team wählen"): string {
  const keys = Object.keys(season.teams).sort((a, b) => season.teams[a]!.short.localeCompare(season.teams[b]!.short, "de"));
  return `<section class="card"><h2>${esc(title)}</h2><div class="picker">${keys
    .map((k) => `<a href="${esc(base)}${esc(k)}">${crest(season.teams[k]!, 34)}<span>${esc(season.teams[k]!.short)}</span></a>`)
    .join("")}</div></section>`;
}

import type { HistoryEvent, TeamInfo, TeamLineup } from "../data";
import { berlin, crest, esc } from "../ui";

const W = 200;
const H = 380;

const initials = (name: string): string =>
  name.split(/\s+/).filter(Boolean).map((w) => w[0]!.toUpperCase()).slice(0, 2).join("");

let uid = 0;

/** Spieler eines Teams aufs Feld setzen. yOf(Reihe, Reihenzahl) gibt die Höhe; below: Name unter dem Punkt. */
function placeTeam(lu: TeamLineup, info: TeamInfo, yOf: (r: number, R: number) => number, mirror: boolean, below0: boolean, goal: Record<string, number>, scale = 1): string {
  const R = lu.rows.length;
  let out = "";
  lu.rows.forEach((row, r) => {
    const y = yOf(r, R);
    const n = row.length;
    const w = n >= 5 ? 164 : Math.min(156, 52 * (n - 1));
    row.forEach((slot, j) => {
      let x = n === 1 ? 100 : 100 - w / 2 + (w * j) / (n - 1);
      if (mirror) x = W - x; // Ligainsider listet aus Sicht der Gegenseite
      const id = `p${++uid}`;
      const p = slot.player;
      const rr = 10 * scale;
      out += `<g><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${rr}" fill="${esc(info.color)}" stroke="#fff" stroke-width="1.6"/>`;
      out += `<text x="${x.toFixed(1)}" y="${(y + 3).toFixed(1)}" text-anchor="middle" font-size="7" font-weight="700" fill="#fff">${esc(initials(p.name))}</text>`;
      if (p.photo) {
        out += `<clipPath id="${id}"><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(rr - 0.8).toFixed(1)}"/></clipPath>`;
        out += `<image href="${esc(p.photo)}" x="${(x - rr + 0.8).toFixed(1)}" y="${(y - rr + 0.8).toFixed(1)}" width="${(2 * rr - 1.6).toFixed(1)}" height="${(2 * rr - 1.6).toFixed(1)}" clip-path="url(#${id})" preserveAspectRatio="xMidYMin slice" onerror="this.remove()"/>`;
      }
      out += `</g>`;
      const alt = slot.alternatives.map((a) => a.name).join(" / ");
      const below = (below0 ? 1 : 0) ^ (n >= 5 && j % 2 === 1 ? 1 : 0);
      const ly = below ? y + rr + 9 : y - (alt ? rr + 12 : rr + 3);
      const edge = n >= 5 && (x < 40 || x > 160);
      const anchor = edge ? (x < 100 ? "start" : "end") : "middle";
      const tx = edge ? (x < 100 ? x - 10 : x + 10) : x;
      const fs = n >= 5 ? 7.2 : 7.8;
      out += `<text x="${tx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${anchor}" font-size="${fs}" font-weight="700" fill="#fff">${esc(p.name)}</text>`;
      if (alt) out += `<text x="${tx.toFixed(1)}" y="${(ly + 8.5).toFixed(1)}" text-anchor="${anchor}" font-size="6.6" fill="#ffd27a">oder ${esc(alt)}</text>`;
      const g = goal[p.id];
      if (g !== undefined && g >= 0.005) {
        out += `<text x="${(x + rr - 2).toFixed(1)}" y="${(y - rr + 4).toFixed(1)}" font-size="6.4" font-weight="700" fill="#fff" stroke="#0b5" stroke-width="2.4" paint-order="stroke">${Math.round(g * 100)}%</text>`;
      }
    });
  });
  return out;
}

const lines = (h: number): string =>
  `<g fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1.2"><rect x="4" y="4" width="192" height="${h - 8}"/><line x1="4" y1="${h / 2}" x2="196" y2="${h / 2}"/><circle cx="100" cy="${h / 2}" r="24"/><rect x="50" y="4" width="100" height="44"/><rect x="50" y="${h - 48}" width="100" height="44"/><rect x="78" y="${h - 20}" width="44" height="16"/><rect x="78" y="4" width="44" height="16"/></g>`;

/** Spielfeld mit beiden voraussichtlichen Aufstellungen: Heim unten, Gast oben. */
export function renderPitch(home: TeamLineup, away: TeamLineup, homeTeam: TeamInfo, awayTeam: TeamInfo, goal: Record<string, number> = {}): string {
  const yy = (r: number, R: number): number => {
    const y0 = r === 0 ? 286 : 255 - (r - 1) * (83 / Math.max(1, R - 2));
    return H - (300 - y0) * 1.35;
  };
  return `<div class="pitchwrap"><svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Voraussichtliche Aufstellungen">${lines(H)}${placeTeam(away, awayTeam, (r, R) => H - yy(r, R), false, false, goal)}${placeTeam(home, homeTeam, yy, true, true, goal)}</svg></div>`;
}

/** Taktiktafel eines Teams: Torwart unten, Sturm oben, über das ganze Feld verteilt. */
export function renderTeamPitch(lu: TeamLineup, info: TeamInfo, goal: Record<string, number> = {}): string {
  const TH = 300;
  const yOf = (r: number, R: number): number => (r === 0 ? TH - 26 : TH - 70 - (r - 1) * ((TH - 120) / Math.max(1, R - 2)));
  return `<div class="pitchwrap"><svg viewBox="0 0 ${W} ${TH}" width="100%" role="img" aria-label="Voraussichtliche Aufstellung ${esc(info.short)}">${lines(TH)}${placeTeam(lu, info, yOf, true, true, goal, 1.25)}</svg></div>`;
}

export function renderMissing(info: TeamInfo, lu: TeamLineup): string {
  const rows = lu.missing.length
    ? lu.missing.map((m) => `<div class="item"><span class="grow"><b>${esc(m.name)}</b><br><span class="muted">${esc(m.note || "–")}</span></span><span class="chip${/Sperre|Karte/.test(m.kind) ? "" : " bad"}">${esc(m.kind)}</span></div>`).join("")
    : `<div class="item"><span class="muted">Keine Ausfälle gemeldet</span></div>`;
  return `<div class="row">${crest(info, 20)}<b>${esc(info.short)}</b><span class="muted">${lu.missing.length} fehlen</span></div><div class="list">${rows}</div>`;
}

export function renderHistory(events: HistoryEvent[], teams: Record<string, TeamInfo>): string {
  if (!events.length) return `<p class="muted">Noch keine Änderungen seit dem ersten Abruf.</p>`;
  const colour: Record<string, string> = { first: "#64748b", formation: "#2f6fe4", in: "#13a150", out: "#e5484d", alt: "#f08a00", missing: "#e5484d", back: "#13a150" };
  return `<div class="tline">${events
    .map((e) => {
      const t = teams[e.team];
      return `<div class="tev"><span class="when">${esc(berlin(e.at)).replace(", ", "<br>")}</span><span class="rail"><i style="background:${colour[e.kind] ?? "#64748b"}"></i></span><div class="what"><div class="row" style="gap:6px">${t ? crest(t, 16) : ""}<b>${esc(t?.short ?? e.team)}</b></div><span class="muted">${esc(e.text)}</span></div></div>`;
    })
    .join("")}</div>`;
}

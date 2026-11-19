import type { Referees, Season } from "../data";
import { esc } from "../ui";

const dec = (x: number | null | undefined, n = 1): string => (x == null ? "–" : x.toFixed(n).replace(".", ","));
const pct = (x: number): string => `${Math.round(x * 100)} %`;

/** Schiedsrichter eines Spiels mit seinen Saisonwerten im Vergleich zum Ligaschnitt. */
export function renderReferee(matchId: number, refs: Referees | null, season: Season, teams: string[] = []): string {
  const name = refs?.upcoming[String(matchId)]?.name;
  if (!refs || !name) return `<p class="muted">Noch nicht angesetzt. FotMob trägt den Schiedsrichter meist wenige Tage vor dem Spiel ein; der Abruf holt ihn dann automatisch.</p>`;
  const r = refs.referees[name];
  const L = refs.league;
  if (!r) return `<p><b>${esc(name)}</b></p><p class="muted">Leitet in dieser Saison sein erstes Bundesliga-Spiel – noch keine Werte.</p>`;
  const rows = [
    ["Gelbe Karten pro Spiel", dec(r.yellow_pg, 2), dec(L.yellow_pg, 2)],
    ["Fouls pro Spiel", dec(r.fouls_pg), dec(L.fouls_pg)],
    ["Elfmeter pro Spiel", dec(r.penalties_pg, 2), dec(L.penalties_pg, 2)],
    ["Rote Karten (gesamt)", String(r.red), "–"],
  ].map(([l, a, b]) => `<div class="srow"><span>${esc(l)}</span><span class="num">${a}</span><span class="num muted">Ø ${b}</span></div>`).join("");
  const rec = teams
    .map((k) => {
      const t = r.teams[k];
      return t ? `<div class="srow"><span>${esc(season.teams[k]?.short ?? k)} unter ihm</span><span class="num">${t.games} Spiele</span><span class="num">${t.points} Pkt.</span></div>` : "";
    })
    .join("");
  return `<p><b>${esc(name)}</b> <span class="muted">· ${r.games} Spiele diese Saison</span></p><div class="catbody">${rows}${rec}</div>
    <p class="muted">Heimsiege ${pct(r.home_win)} · Remis ${pct(r.draw)} · Auswärtssiege ${pct(r.away_win)}. Quelle: FotMob, eigene Auswertung.</p>`;
}

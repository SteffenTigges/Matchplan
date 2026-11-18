import type { MetricDef, TeamStats } from "../data";
import { esc } from "../ui";

const de = (x: number, d: number): string => x.toFixed(d).replace(".", ",");

export function formatMetric(v: number, fmt: string): string {
  switch (fmt) {
    case "pct": return `${Math.round(v * 100)} %`;
    case "dec1": return de(v, 1);
    case "dec2": return de(v, 2);
    case "signed0": return `${v > 0 ? "+" : ""}${Math.round(v)}`;
    case "signed1": return `${v > 0 ? "+" : ""}${de(v, 1)}`;
    default: return String(Math.round(v));
  }
}

const chip = (rank: number): string => `<span class="chip ${rank <= 4 ? "good" : rank >= 13 ? "bad" : "mid"}">${rank}.</span>`;

/** Saisonwerte eines Teams in Kategorien, je Kennzahl mit Ligarang. */
export function renderTeamStats(key: string, stats: TeamStats): string {
  const team = stats.teams[key];
  if (!team) return "";
  const matches = typeof team.matches === "number" ? team.matches : 0;
  const row = (m: MetricDef): string => {
    const e = team[m.key];
    if (!e || typeof e === "number") return "";
    return `<div class="srow"><span>${esc(m.label)}${m.approx ? '<span class="tag">Näherung</span>' : ""}</span><span class="num">${esc(formatMetric(e.value, m.fmt))}</span>${chip(e.rank)}</div>`;
  };
  const nav = `<div class="seg">${stats.categories.map((c, i) => `<a href="#" onclick="event.preventDefault();const d=document.getElementById('tc-${i}');d.open=true;d.scrollIntoView({behavior:'smooth'})">${esc(c)}</a>`).join("")}</div>`;
  const cats = stats.categories
    .map((c, i) => {
      const rows = stats.metrics.filter((m) => m.category === c).map(row).join("");
      return rows ? `<details class="cat" id="tc-${i}" ${i < 3 ? "open" : ""}><summary><b>${esc(c)}</b></summary><div class="catbody">${rows}</div></details>` : "";
    })
    .join("");
  return `<section class="card"><h2>Saisonwerte</h2>${nav}${cats}<p class="muted">Rang 1 = Bestwert der Liga · Daten: FotMob · ${matches} Spiele</p></section>`;
}

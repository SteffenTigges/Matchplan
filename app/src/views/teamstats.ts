import type { MetricDef, Season, TeamStats } from "../data";
import { crest, esc } from "../ui";

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

const cls = (rank: number): string => (rank <= 4 ? "good" : rank >= 13 ? "bad" : "mid");
const chip = (rank: number, href: string): string => `<a class="chip ${cls(rank)}" href="${esc(href)}" aria-label="Rangliste aller Teams">${rank}. ›</a>`;

/** Saisonwerte eines Teams in Kategorien, je Kennzahl mit Ligarang. */
export function renderTeamStats(key: string, stats: TeamStats): string {
  const team = stats.teams[key];
  if (!team) return "";
  const matches = typeof team.matches === "number" ? team.matches : 0;
  const row = (m: MetricDef): string => {
    const e = team[m.key];
    if (!e || typeof e === "number" || e.value == null || e.rank == null) return "";
    return `<div class="srow"><span>${esc(m.label)}${m.approx ? '<span class="tag">Näherung</span>' : ""}</span><span class="num">${esc(formatMetric(e.value, m.fmt))}</span>${chip(e.rank, `#rang/${m.key}/${key}`)}</div>`;
  };
  const nav = `<div class="seg">${stats.categories.map((c, i) => `<a href="#" onclick="event.preventDefault();const d=document.getElementById('tc-${i}');d.open=true;d.scrollIntoView({behavior:'smooth'})">${esc(c)}</a>`).join("")}</div>`;
  const cats = stats.categories
    .map((c, i) => {
      const rows = stats.metrics.filter((m) => m.category === c).map(row).join("");
      return rows ? `<details class="cat" id="tc-${i}" ${i < 3 ? "open" : ""}><summary><b>${esc(c)}</b></summary><div class="catbody">${rows}</div></details>` : "";
    })
    .join("");
  return `<section class="card"><h2>Saisonwerte</h2>${nav}${cats}<p class="muted">Rang antippen: Rangliste aller 18 Teams · Rang 1 = Bestwert der Liga · Daten: FotMob · ${matches} Spiele</p></section>`;
}

/** Rangliste aller Teams für eine Kennzahl; das ausgewählte Team ist hervorgehoben. */
export function renderMetricRanking(metric: string, highlight: string, stats: TeamStats, season: Season): string {
  const m = stats.metrics.find((x) => x.key === metric);
  if (!m) return "";
  const rows = Object.entries(stats.teams)
    .flatMap(([key, t]) => {
      const e = t[metric];
      return e && typeof e !== "number" && e.value != null && e.rank != null ? [{ key, value: e.value, rank: e.rank, n: typeof t.matches === "number" ? t.matches : 0 }] : [];
    })
    .sort((a, b) => a.rank - b.rank || a.key.localeCompare(b.key));
  const items = rows
    .map((r) => {
      const t = season.teams[r.key] ?? { name: r.key, short: r.key, color: "#64748b", crest: "" };
      return `<a class="item${r.key === highlight ? " me" : ""}" href="#team/${esc(r.key)}"><span class="chip ${cls(r.rank)}" style="min-width:34px;text-align:center">${r.rank}.</span>${crest(t, 24)}<span class="grow"><b>${esc(t.short)}</b><br><span class="muted">${r.n} Spiele</span></span><span class="num" style="font-weight:700">${esc(formatMetric(r.value, m.fmt))}</span></a>`;
    })
    .join("");
  return `<section class="card"><h2>${esc(m.label)}${m.approx ? '<span class="tag">Näherung</span>' : ""}</h2><p class="muted">${esc(m.category)} · ${m.higher_is_better ? "höher ist besser" : "niedriger ist besser"} · Daten: FotMob</p></section><div class="list">${items}</div>`;
}

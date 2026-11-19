import type { CareerEntry, PlayerProfile, PlayerRow, Season, TeamInfo } from "../data";
import { crest, esc, photo } from "../ui";

const info = (s: Season, k: string | null): TeamInfo | null => (k ? s.teams[k] ?? null : null);
export const fotmobPhoto = (id: number): string => `https://images.fotmob.com/image_resources/playerimages/${id}.png`;
export const normSearch = (s: string): string => norm(s);
const norm = (s: string): string => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ø/g, "o").replace(/ł/g, "l").toLowerCase();
const de = (x: number, d: number): string => x.toFixed(d).replace(".", ",");
const pctColor = (q: number): string => (q >= 80 ? "#2f6fe4" : q >= 60 ? "#13a150" : q >= 35 ? "#f08a00" : "#e5484d");
const rt = (r: number | null): string =>
  r == null ? "" : `<span class="rt" style="background:${r >= 8 ? "#2f6fe4" : r >= 7 ? "#13a150" : r >= 6.5 ? "#f08a00" : "#e5484d"}">${de(r, 1)}</span>`;

export function filterPlayers(rows: PlayerRow[], q: string): PlayerRow[] {
  const n = norm(q.trim());
  return n ? rows.filter((r) => norm(r.name).includes(n)) : rows;
}

export function renderPlayerList(rows: PlayerRow[], season: Season, q: string): string {
  const list = filterPlayers(rows, q);
  const teams = Object.keys(season.teams).filter((k) => list.some((r) => r.team === k)).sort((a, b) => season.teams[a].short.localeCompare(season.teams[b].short, "de"));
  const groups = teams
    .map((k) => {
      const t = season.teams[k];
      const items = list
        .filter((r) => r.team === k)
        .sort((a, b) => b.minutes - a.minutes)
        .map((r) => `<a class="item" href="#spieler/${r.id}" data-s="${esc(norm(r.name))}">${photo(fotmobPhoto(r.id), r.name, 36)}<span class="grow"><b>${esc(r.name)}</b><br><span class="muted">${esc(r.pos ?? "")}${r.age ? ` · ${r.age} J.` : ""} · ${r.apps} Spiele</span></span>${rt(r.rating)}</a>`)
        .join("");
      return `<section class="pgroup" data-team="${esc(k)}"><div class="row" style="gap:8px;margin:6px 0">${crest(t, 20)}<h3>${esc(t.short)}</h3></div><div class="list">${items}</div></section>`;
    })
    .join("");
  return `<input class="search" id="psearch" type="search" placeholder="Spieler suchen …" value="${esc(q)}" autocomplete="off" aria-label="Spieler suchen">${groups || '<p class="muted">Kein Spieler gefunden.</p>'}`;
}

const years = (e: CareerEntry): string => {
  const a = e.start?.slice(0, 4);
  const b = e.end?.slice(0, 4);
  if (!a) return "–";
  if (!b) return `seit ${a}`;
  return a === b ? a : `${a}–${b}`;
};

function timeline(title: string, entries: CareerEntry[], youth = false): string {
  if (!entries.length) return "";
  const sorted = [...entries].sort((x, y) => (x.start ?? "").localeCompare(y.start ?? ""));
  return `<h3>${esc(title)}</h3><div>${sorted
    .map((e) => `<div class="tl${youth ? " youth" : ""}"><span class="yr">${esc(years(e))}</span><span class="rail"></span><div class="body"><b>${esc(e.team)}</b>${e.kind ? ` <span class="chip">${esc(e.kind)}</span>` : ""}<span class="muted">${e.apps != null ? `${e.apps} Spiele` : "–"}${e.goals != null ? ` · ${e.goals} Tore` : ""}</span></div></div>`)
    .join("")}</div>`;
}

const money = (v: number): string => (v >= 1e6 ? `${de(v / 1e6, 1)} Mio. €` : `${Math.round(v / 1e3)} Tsd. €`);

export function renderPlayer(p: PlayerProfile | null, row: PlayerRow | null, season: Season): string {
  const id = p?.id ?? row?.id ?? 0;
  const name = p?.name ?? row?.name ?? "";
  const t = info(season, p ? p.team : row?.team ?? null); // mit Profil zählt dessen aktueller Verein
  const color = t?.color ?? "#334155";
  const main = p?.positions.find((x) => x.main);
  const chips = [
    main?.label, p?.age != null ? `${p.age} Jahre` : null, p?.height_cm ? `${p.height_cm} cm` : null,
    p?.foot ? `Fuß: ${p.foot}` : null, p?.country, p?.market_value ? money(p.market_value) : null,
    p?.contract_end ? `Vertrag bis ${p.contract_end.slice(0, 4)}` : null, p?.shirt != null ? `Nr. ${p.shirt}` : null,
  ].filter(Boolean);
  const hero = `<div class="hero" style="background:linear-gradient(135deg,${esc(color)} 0%,color-mix(in srgb,${esc(color)} 55%,#000) 100%)">
    <div class="row">${photo(fotmobPhoto(id), name, 64)}<div style="min-width:0"><div class="tlab">${esc(t?.name ?? p?.team_name ?? "")}</div><h2 style="color:#fff">${esc(name)}</h2></div><span style="margin-left:auto">${rt(row?.rating ?? null)}</span></div>
    <div class="pills">${chips.map((c) => `<span class="pill">${esc(c)}</span>`).join("")}</div></div>`;
  const season_ = row ? `<section class="card"><div class="kpis"><div class="kpi"><b>${row.apps}</b><span>Einsätze</span></div><div class="kpi"><b>${row.minutes}</b><span>Minuten</span></div><div class="kpi"><b>${row.rating != null ? de(row.rating, 2) : "–"}</b><span>Ø Note</span></div></div></section>` : "";
  if (!p) return `${hero}${season_}<section class="card"><p class="muted">Profil wird beim nächsten Abruf geladen.</p></section>`;

  const groups = [...new Set(p.stats.map((s) => s.group))];
  const stats = groups.length
    ? `<section class="card"><h2>Saisonwerte im Vergleich</h2><p class="muted">Balken: Perzentil pro 90 Minuten gegenüber Spielern derselben Position in der Liga.</p>${groups
        .map((g, i) => `<details class="cat" ${i < 2 ? "open" : ""}><summary><b>${esc(g)}</b></summary><div class="catbody">${p.stats
          .filter((s) => s.group === g)
          .map((s) => {
            const q = Math.round(s.pct ?? 0);
            const pct = s.fmt === "percent";
            const val = s.value != null ? esc(String(s.value).replace(".", ",")) + (pct ? " %" : "") : "–";
            return `<div class="prow"><span>${esc(s.title)}</span><span><span class="pv">${val}</span>${s.per90 != null && !pct ? `<span class="pp">${de(s.per90, 2)} /90</span>` : ""}</span>${s.pct != null ? `<div class="pb"><i style="width:${q}%;background:${pctColor(q)}"></i></div><span class="pq">${q}</span>` : ""}</div>`;
          })
          .join("")}</div></details>`)
        .join("")}<p class="muted">Quelle: FotMob</p></section>`
    : "";
  const c = p.career;
  const careerHtml = [timeline("Jugend", c.youth, true), timeline("Profi", c.senior), timeline("Nationalmannschaft", c.national), timeline("Junioren-Nationalteams", c.national_youth, true)].join("");
  const career = careerHtml ? `<section class="card"><h2>Karriere</h2>${careerHtml}<p class="muted">Quelle: FotMob · frühe Jugendvereine nicht immer vollständig</p></section>` : "";
  const transfers = p.transfers.length
    ? `<section class="card"><h2>Transfers</h2><div class="list">${p.transfers
        .map((x) => `<div class="item"><span class="num muted" style="width:44px">${esc(x.date?.slice(0, 4) ?? "")}</span><span class="grow">${esc(x.from)} → <b>${esc(x.to)}</b></span><span class="chip">${esc(x.fee ?? "–")}</span></div>`)
        .join("")}</div></section>`
    : "";
  return hero + season_ + stats + career + transfers;
}

export function renderSquad(rows: PlayerRow[], team: string): string {
  const mine = rows.filter((r) => r.team === team).sort((a, b) => b.minutes - a.minutes);
  if (!mine.length) return "";
  return `<section class="card"><h3>Kader (nach Einsatzminuten)</h3><div class="list">${mine
    .map((r) => `<a class="item" href="#spieler/${r.id}">${photo(fotmobPhoto(r.id), r.name, 30)}<span class="grow"><b>${esc(r.name)}</b><br><span class="muted">${esc(r.pos ?? "")} · ${r.minutes} Min.</span></span>${rt(r.rating)}</a>`)
    .join("")}</div></section>`;
}

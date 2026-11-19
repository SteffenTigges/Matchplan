import type { Match, ModelCheck, Prediction, Scorer, Season, TeamInfo } from "../data";
import { crest, esc, photo } from "../ui";

const team = (s: Season, key: string): TeamInfo => s.teams[key] ?? { name: key, short: key, color: "#64748b", crest: "" };
const pct = (x: number): string => `${Math.round(x * 100)} %`;
const dec = (x: number | null | undefined, n = 1): string => (x == null ? "–" : x.toFixed(n).replace(".", ","));

/** Dreigeteilter Balken Sieg / Remis / Niederlage in Vereinsfarben. */
export function chanceBar(p: Prediction, h: TeamInfo, a: TeamInfo): string {
  const [ph, pd, pa] = p.probs;
  const seg = (x: number, bg: string, label: string): string =>
    `<i style="flex:${Math.max(x, 0.04)};background:${esc(bg)}" title="${esc(label)}">${x >= 0.12 ? pct(x) : ""}</i>`;
  return `<div class="chance">${seg(ph, h.color, h.short)}${seg(pd, "#8f9bb0", "Remis")}${seg(pa, a.color, a.short)}</div>`;
}

const allScorers = (p: Prediction): (Scorer & { side: "home" | "away" })[] =>
  [...p.scorers.home.map((s) => ({ ...s, side: "home" as const })), ...p.scorers.away.map((s) => ({ ...s, side: "away" as const }))].sort((x, y) => y.p - x.p);

/** Kurzzeile für die Spieltagsliste. */
export function tipLine(p: Prediction, season: Season): string {
  const h = team(season, p.home);
  const a = team(season, p.away);
  const top = allScorers(p)[0];
  return `<div class="row" style="justify-content:space-between"><span class="chip">Tipp ${p.tip[0]}:${p.tip[1]}</span>${
    top && top.p > 0 ? `<span class="muted">Trifft am ehesten: <b>${esc(top.name)}</b> ${pct(top.p)}</span>` : ""
  }</div>${chanceBar(p, h, a)}`;
}

function sentence(p: Prediction, h: TeamInfo, a: TeamInfo): string {
  const [ph, pd, pa] = p.probs;
  const best = Math.max(ph, pd, pa);
  const who = best === ph ? `${h.short} gewinnt wahrscheinlich (${pct(ph)})` : best === pa ? `${a.short} gewinnt wahrscheinlich (${pct(pa)})` : `Am ehesten ein Remis (${pct(pd)})`;
  const close = best < 0.45 ? " Das Spiel gilt als offen." : "";
  return `${who}.${close} Erwartete Tore ${dec(p.xg[0])} : ${dec(p.xg[1])}.`;
}

/** Zeile „Wir gegen sie“: linker und rechter Wert, Balken zugunsten des besseren. */
function vsRow(label: string, l: number | null, r: number | null, higherBetter: boolean, fmt: (x: number | null) => string, h: TeamInfo, a: TeamInfo): string {
  const lv = l ?? 0;
  const rv = r ?? 0;
  const tot = lv + rv || 1;
  const lw = higherBetter ? lv >= rv : lv <= rv;
  return `<span class="l">${fmt(l)}</span><span class="lab">${esc(label)}</span><span class="r">${fmt(r)}</span>
    <span class="bb"><i class="${lw ? "w" : ""}" style="flex:${lv / tot};background:${esc(h.color)}"></i><i class="${!lw ? "w" : ""}" style="flex:${rv / tot};background:${esc(a.color)}"></i></span>`;
}

function scorerList(p: Prediction, season: Season, limit = 10): string {
  const rows = allScorers(p).filter((s) => s.p > 0).slice(0, limit);
  if (!rows.length) return `<p class="muted">Noch keine voraussichtliche Aufstellung.</p>`;
  return `<div class="list">${rows
    .map((s) => {
      const t = team(season, s.side === "home" ? p.home : p.away);
      const link = s.fm_id ? ` href="#spieler/${s.fm_id}"` : "";
      return `<a class="item"${link}>${photo(s.photo, s.name, 34)}<span class="grow"><b>${esc(s.name)}</b><br><span class="muted">${s.minutes < 80 ? "Position offen · " : ""}ca. ${Math.round(s.minutes)} Min.</span></span>${crest(t, 20)}<span class="num" style="font-weight:700;width:46px;text-align:right">${pct(s.p)}</span></a>`;
    })
    .join("")}</div>`;
}

export function renderPrognosis(m: Match, p: Prediction, season: Season): string {
  const h = team(season, m.home);
  const a = team(season, m.away);
  const w = p.why;
  const [ph, pd, pa] = p.probs;

  const head = `<section class="card"><h2>Prognose</h2>
    <div class="fx"><div class="t">${crest(h, 30)}</div><div class="mid"><div class="tlab">Tipp</div><div class="score">${p.tip[0]}:${p.tip[1]}</div><div class="muted">${pct(p.tip_prob)} genau dieses Ergebnis</div></div><div class="t">${crest(a, 30)}</div></div>
    <p>${esc(sentence(p, h, a))}</p>
    ${chanceBar(p, h, a)}
    <div class="kpis"><div class="kpi"><span class="tlab">${esc(h.short)}</span><b>${pct(ph)}</b></div><div class="kpi"><span class="tlab">Remis</span><b>${pct(pd)}</b></div><div class="kpi"><span class="tlab">${esc(a.short)}</span><b>${pct(pa)}</b></div></div>
    <a class="btn" href="#prognose/${m.id}">Alle Ergebnisse &amp; Wahrscheinlichkeiten ›</a></section>`;

  const abs = (side: "home" | "away"): string => {
    const list = w.absences[side].filter((x) => x.fm_id !== null && (x.xg_share > 0 || x.minutes_share > 0.3));
    return list.length ? list.map((x) => esc(x.name)).join(", ") : "keine wichtigen";
  };
  const factor = (f: [number, number]): number => Math.round((f[0] - 1) * 100);
  const why = `<section class="card"><h2>Warum?</h2>
    <div class="vs">
      ${vsRow("Angriff: xG pro Spiel", w.xgf[0], w.xgf[1], true, (x) => dec(x, 2), h, a)}
      ${vsRow("Abwehr: zugelassene xG", w.xga[0], w.xga[1], false, (x) => dec(x, 2), h, a)}
      ${vsRow("Form: Punkte pro Spiel (letzte 5)", w.form[0], w.form[1], true, (x) => dec(x, 1), h, a)}
    </div>
    <p class="muted">Heimvorteil: Heimteams schießen in der Liga im Schnitt ${dec(w.means[0], 2)} Tore, Gäste ${dec(w.means[1], 2)}.</p>
    <p class="muted">Personal (Näherung): Bei ${esc(h.short)} fehlen ${abs("home")}${factor(w.absence_factor[0]) ? ` (eigene Tore ${factor(w.absence_factor[0])} %)` : ""}; bei ${esc(a.short)} fehlen ${abs("away")}${factor(w.absence_factor[1]) ? ` (eigene Tore ${factor(w.absence_factor[1])} %)` : ""}.</p></section>`;

  const odds = p.odds
    ? `<section class="card"><h2>Gegencheck</h2><p class="muted">Implizite Wahrscheinlichkeit aus den Quoten (${esc(p.odds.source)}, Buchmacher-Marge herausgerechnet). Elo nicht verfügbar: ClubElo ist seit Wochen nicht erreichbar.</p>
        <div class="srow"><span></span><span class="tlab">Modell</span><span class="tlab">Buchmacher</span></div>
        ${[["Sieg " + h.short, ph, p.odds.home], ["Remis", pd, p.odds.draw], ["Sieg " + a.short, pa, p.odds.away]]
          .map(([l, x, y]) => `<div class="srow"><span>${esc(l)}</span><span class="num">${pct(x as number)}</span><span class="num">${pct(y as number)}</span></div>`)
          .join("")}</section>`
    : "";

  const scorers = `<section class="card"><h2>Wer trifft?</h2><p class="muted">Wahrscheinlichkeit für mindestens ein Tor, aus der voraussichtlichen Aufstellung und den Saison-xG pro 90 Minuten.</p>${scorerList(p, season)}</section>`;

  const calc = `<details class="card"><summary class="tlab">Rechenweg</summary>
    <p class="muted">λ ${esc(h.short)} = ${dec(w.means[0], 2)} (Heimschnitt) × ${dec(w.attack[0], 2)} (Angriff ${esc(h.short)}) × ${dec(w.defence[1], 2)} (Abwehr ${esc(a.short)}) × Ausfälle = <b>${dec(p.xg[0], 2)}</b></p>
    <p class="muted">λ ${esc(a.short)} = ${dec(w.means[1], 2)} (Auswärtsschnitt) × ${dec(w.attack[1], 2)} × ${dec(w.defence[0], 2)} × Ausfälle = <b>${dec(p.xg[1], 2)}</b></p>
    <p class="muted">Angriff und Abwehr: xG bzw. zugelassene xG pro Spiel geteilt durch den Ligaschnitt, 70 % Saison und 30 % letzte 5 Spiele, bei wenigen Spielen zum Schnitt hin gezogen (${w.n[0]} bzw. ${w.n[1]} Spiele). Jedes Ergebnis per Poisson-Verteilung, kleine Ergebnisse mit Dixon-Coles-Korrektur (ρ = ${dec(w.rho, 2)}).</p></details>`;

  return head + why + odds + scorers + calc;
}

export function renderAllResults(m: Match, p: Prediction, season: Season): string {
  const h = team(season, m.home);
  const a = team(season, m.away);
  const cells = p.matrix.flatMap((r, i) => r.map((v, j) => ({ i, j, v }))).sort((x, y) => y.v - x.v);
  const shown = cells.reduce((s, c) => s + c.v, 0);
  const max = cells[0]?.v || 1;
  const list = `<section class="card"><h2>Alle Ergebnisse</h2><div class="list">${cells
    .map((c) => `<div class="item"><span class="num" style="font-weight:700;width:38px">${c.i}:${c.j}</span><span class="grow"><span class="pbar"><i style="width:${(c.v / max) * 100}%;background:${esc(c.i > c.j ? h.color : c.i < c.j ? a.color : "#8f9bb0")}"></i></span></span><span class="num" style="width:52px;text-align:right">${dec(c.v * 100, 1)} %</span></div>`)
    .join("")}</div><p class="muted">Alle anderen Ergebnisse (6 Tore oder mehr für ein Team): ${dec(Math.max(0, 1 - shown) * 100, 1)} %.</p></section>`;

  const heat = `<section class="card"><h2>Ergebnistabelle</h2><p class="muted">Zeilen: Tore ${esc(h.short)}, Spalten: Tore ${esc(a.short)}.</p>
    <div class="heat"><span></span>${[0, 1, 2, 3, 4, 5].map((j) => `<b>${j}</b>`).join("")}${p.matrix
      .map((r, i) => `<b>${i}</b>${r.map((v) => `<span style="background:color-mix(in srgb,var(--accent) ${Math.round((v / max) * 85)}%,var(--surface2))">${dec(v * 100, 0)}</span>`).join("")}`)
      .join("")}</div></section>`;

  const mk = p.markets;
  const markets = `<section class="card"><h2>Weitere Wahrscheinlichkeiten</h2><div class="kpis">
    <div class="kpi"><span class="tlab">Über 2,5 Tore</span><b>${pct(mk.over25)}</b></div>
    <div class="kpi"><span class="tlab">Unter 2,5 Tore</span><b>${pct(1 - mk.over25)}</b></div>
    <div class="kpi"><span class="tlab">Beide treffen</span><b>${pct(mk.btts)}</b></div>
    <div class="kpi"><span class="tlab">${esc(h.short)} zu null</span><b>${pct(mk.home_clean_sheet)}</b></div>
    <div class="kpi"><span class="tlab">${esc(a.short)} zu null</span><b>${pct(mk.away_clean_sheet)}</b></div>
    <div class="kpi"><span class="tlab">Erwartete Tore</span><b>${dec(p.xg[0] + p.xg[1])}</b></div></div></section>`;

  return `<section class="card"><div class="row">${crest(h, 26)}<b>${esc(h.short)}</b><span class="grow"></span><b>${esc(a.short)}</b>${crest(a, 26)}</div>${chanceBar(p, h, a)}</section>` + list + heat + markets;
}

/** Bei beendeten Spielen: Was war vorhergesagt, was stimmte? */
export function renderPriorPrediction(m: Match, p: Prediction, season: Season): string {
  if (!m.score) return "";
  const [hg, ag] = m.score;
  const res = Math.sign(hg - ag);
  const tipRes = Math.sign(p.tip[0] - p.tip[1]);
  const verdict = p.tip[0] === hg && p.tip[1] === ag ? "Ergebnis genau getroffen" : tipRes === res ? "Tendenz getroffen" : "Daneben";
  const cls = verdict === "Daneben" ? "bad" : "good";
  const prob = res > 0 ? p.probs[0] : res === 0 ? p.probs[1] : p.probs[2];
  const hits = (side: "home" | "away", key: string): string => {
    const n = p.lineup_hits?.[side];
    return n == null ? "" : `<p class="muted">Aufstellung ${esc(team(season, key).short)}: Ligainsider lag bei ${n} von 11 richtig.</p>`;
  };
  return `<section class="card"><h2>Prognose vor dem Spiel</h2>
    <div class="row"><span class="chip">Tipp war ${p.tip[0]}:${p.tip[1]}</span><span class="chip ${cls}">${verdict}</span></div>
    <p class="muted">Dem tatsächlichen Ausgang gab das Modell ${pct(prob)}.</p>${hits("home", m.home)}${hits("away", m.away)}</section>`;
}

export function renderModelCheck(mc: ModelCheck | null): string {
  if (!mc || !mc.check.matches) return "";
  const c = mc.check;
  const cal = mc.calibration;
  const odds = c.brier_odds != null
    ? `<p class="muted">Brier-Score Modell ${dec(c.brier_model_same, 2)} gegen Buchmacher ${dec(c.brier_odds, 2)} (${c.odds_matches} Spiele mit Schlussquoten; kleiner ist besser).</p>`
    : "";
  const rows = c.by_matchday
    .map((d) => `<div class="srow"><span>${d.md}. Spieltag</span><span class="num">${d.tendency}/${d.matches} Tendenz · ${d.exact} genau</span><span class="num">${dec(d.brier, 2)}</span></div>`)
    .join("");
  return `<section class="card"><h2>Modellprüfung</h2>
    <p class="muted">Jedes beendete Spiel wurde nachträglich nur mit den Daten der Spieltage davor vorhergesagt.</p>
    <div class="kpis"><div class="kpi"><span class="tlab">Tendenz richtig</span><b>${pct(c.tendency_rate ?? 0)}</b></div><div class="kpi"><span class="tlab">Genau richtig</span><b>${pct(c.exact_rate ?? 0)}</b></div><div class="kpi"><span class="tlab">Brier-Score</span><b>${dec(c.brier, 2)}</b></div></div>
    ${odds}
    <details><summary class="tlab">Je Spieltag</summary>${rows}</details>
    <p class="muted">Kalibriert an ${cal.matches} Spielen${cal.seasons ? ` der Saisons ${esc(cal.seasons)}` : ""}: Heimschnitt ${dec(cal.home, 2)}, Auswärtsschnitt ${dec(cal.away, 2)}, ρ ${dec(cal.rho, 2)}.</p></section>`;
}

import type { FotmobMatch, LiveMatch, Match, MatchEvent, Season, TeamInfo } from "../data";
import { berlin, crest, esc } from "../ui";

const info = (s: Season, k: string): TeamInfo => s.teams[k] ?? { name: k, short: k, color: "#64748b", crest: "" };
const LIVE_WINDOW_MS = 150 * 60 * 1000;

/** Läuft das Spiel gerade (Anpfiff vorbei, noch nicht beendet, höchstens 2,5 h her)? */
export function isLive(m: Match, now: Date): boolean {
  if (m.finished || !m.kickoff) return false;
  const k = new Date(m.kickoff).getTime();
  return now.getTime() >= k && now.getTime() <= k + LIVE_WINDOW_MS;
}

/** Ungefähre Spielminute aus der Anstoßzeit (15 Minuten Pause), wenn noch keine Live-Daten da sind. */
export function approxMinute(kickoff: string, now: Date): string {
  const el = Math.floor((now.getTime() - new Date(kickoff).getTime()) / 60000);
  if (el < 0) return "";
  if (el <= 47) return `~${Math.max(1, el)}'`;
  if (el <= 62) return "Halbzeit";
  return `~${Math.min(el - 15, 90)}'`;
}

const minuteOf = (e: MatchEvent): string => (e.min == null ? "" : `${e.min}${e.plus ? `+${e.plus}` : ""}'`);

const link = (id: number | null | undefined, name: string | null | undefined): string =>
  !name ? "" : id ? `<a class="plink" href="#spieler/${id}">${esc(name)}</a>` : esc(name);

function eventRow(e: MatchEvent, h: TeamInfo, a: TeamInfo): string {
  const t = e.home == null ? null : e.home ? h : a;
  const side = t ? crest(t, 18) : "";
  let icon = "";
  let body = "";
  if (e.type === "goal") {
    icon = "⚽";
    body = `<b>${e.score ? `${e.score[0]}:${e.score[1]} ` : ""}${link(e.player_id, e.player)}</b>${e.penalty ? ' <span class="chip">Elfmeter</span>' : ""}${e.own_goal ? ' <span class="chip bad">Eigentor</span>' : ""}${e.assist ? `<br><span class="muted">Vorlage ${esc(e.assist)}</span>` : ""}`;
  } else if (e.type === "card") {
    icon = `<i class="card-ico ${e.card}"></i>`;
    body = `${link(e.player_id, e.player)} <span class="muted">${e.card === "red" ? "Rot" : e.card === "yellowred" ? "Gelb-Rot" : "Gelb"}</span>`;
  } else if (e.type === "sub") {
    icon = "⇄";
    body = `<span class="in">▲ ${link(e.in_id, e.in)}</span> <span class="out muted">▼ ${link(e.out_id, e.out)}</span>`;
  } else if (e.type === "half") {
    return `<div class="tick sep"><span>${e.text === "HT" ? "Halbzeit" : e.text === "FT" ? "Abpfiff" : esc(e.text ?? "")}</span></div>`;
  } else if (e.type === "added") {
    return `<div class="tick sep"><span>${esc((e.text ?? "").replace("minutes added", "Minuten Nachspielzeit").replace("minute added", "Minute Nachspielzeit"))}</span></div>`;
  } else {
    icon = "📺";
    body = esc(e.text ?? "Videobeweis");
  }
  return `<div class="tick"><span class="num tmin">${minuteOf(e)}</span><span class="ticon">${icon}</span><span class="grow">${body}</span>${side}</div>`;
}

/** Ereignisse des Spiels: im Liveticker neueste oben, im Spielbericht in Spielreihenfolge. */
export function renderEvents(events: MatchEvent[] | undefined, m: Match, season: Season, newestFirst = false): string {
  if (!events?.length) return "";
  const h = info(season, m.home);
  const a = info(season, m.away);
  const list = newestFirst ? [...events].reverse() : events;
  return `<section class="card"><h3>${newestFirst ? "Liveticker" : "Spielverlauf"}</h3><div class="ticker">${list.map((e) => eventRow(e, h, a)).join("")}</div></section>`;
}

/** xG-Verlauf: aufsummierte Chancenqualität beider Teams über die Spielzeit, Tore markiert. */
export function renderXgTimeline(fm: Pick<FotmobMatch, "shots">, m: Match, season: Season): string {
  const shots = (fm.shots ?? []).filter((s) => s.min != null && !s.own_goal).sort((x, y) => x.min! - y.min!);
  if (!shots.length) return "";
  const h = info(season, m.home);
  const a = info(season, m.away);
  const end = Math.max(90, ...shots.map((s) => s.min!));
  const W = 320;
  const H = 120;
  const tot = (team: string) => shots.filter((s) => s.team === team).reduce((t, s) => t + (s.xg ?? 0), 0);
  const max = Math.max(1, tot(m.home), tot(m.away));
  const X = (mi: number) => (mi / end) * (W - 10) + 5;
  const Y = (v: number) => H - 8 - (v / max) * (H - 20);
  const path = (team: string) => {
    let v = 0;
    let d = `M${X(0)},${Y(0)}`;
    const goals: string[] = [];
    for (const s of shots.filter((x) => x.team === team)) {
      d += ` H${X(s.min!).toFixed(1)}`;
      v += s.xg ?? 0;
      d += ` V${Y(v).toFixed(1)}`;
      if (s.result === "goal") goals.push(`<circle cx="${X(s.min!).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="3.5" fill="#fff" stroke="currentColor" stroke-width="2"/>`);
    }
    d += ` H${X(end)}`;
    return { d, goals, v };
  };
  const ph = path(m.home);
  const pa = path(m.away);
  const de = (x: number) => x.toFixed(2).replace(".", ",");
  return `<section class="card"><h3>xG-Verlauf</h3>
    <svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="xG-Verlauf"><line x1="${X(45)}" y1="6" x2="${X(45)}" y2="${H - 8}" stroke="var(--line)" stroke-dasharray="3 3"/>
      <g style="color:${esc(h.color)}"><path d="${ph.d}" fill="none" stroke="currentColor" stroke-width="2.4"/>${ph.goals.join("")}</g>
      <g style="color:${esc(a.color)}"><path d="${pa.d}" fill="none" stroke="currentColor" stroke-width="2.4" stroke-dasharray="5 3"/>${pa.goals.join("")}</g></svg>
    <div class="row" style="justify-content:space-between"><span><b>${esc(h.short)}</b> ${de(ph.v)} xG</span><span class="muted">Kreis = Tor</span><span><b>${esc(a.short)}</b> ${de(pa.v)} xG</span></div></section>`;
}

type P = { id?: number; team?: string; name?: string; minutes?: number; rating?: number; goals?: number; assists?: number; xg?: number; xa?: number; shots?: number; key_passes?: number; touches_box?: number; tackles?: number; interceptions?: number; duels_won?: number; duels_lost?: number };

/** Spielerstatistik je Team, sortiert nach Note. */
export function renderPlayerTable(fm: Pick<FotmobMatch, "players">, m: Match, season: Season): string {
  const ps = (fm.players ?? []) as P[];
  if (!ps.some((p) => p.minutes)) return "";
  const n = (v: number | undefined, d = 0) => (v == null ? "–" : d ? v.toFixed(d).replace(".", ",") : String(v));
  const table = (key: string) => {
    const t = info(season, key);
    const rows = ps.filter((p) => p.team === key && p.minutes).sort((x, y) => (y.rating ?? 0) - (x.rating ?? 0));
    if (!rows.length) return "";
    return `<h4 class="row" style="gap:6px;margin:10px 0 4px">${crest(t, 18)}${esc(t.short)}</h4><div class="ptable"><span class="tlab">Spieler</span><span class="tlab">Min</span><span class="tlab">Note</span><span class="tlab">T/V</span><span class="tlab">xG</span><span class="tlab">xA</span><span class="tlab">Sch.</span><span class="tlab">Zw.</span>${rows
      .map((p) => `<span class="cut">${p.id ? `<a class="plink" href="#spieler/${p.id}">${esc(p.name ?? "")}</a>` : esc(p.name ?? "")}</span><span class="num">${n(p.minutes)}</span><span class="num">${n(p.rating, 1)}</span><span class="num">${n(p.goals)}/${n(p.assists)}</span><span class="num">${n(p.xg, 2)}</span><span class="num">${n(p.xa, 2)}</span><span class="num">${n(p.shots)}</span><span class="num">${p.duels_won != null ? `${p.duels_won}/${(p.duels_won ?? 0) + (p.duels_lost ?? 0)}` : "–"}</span>`)
      .join("")}</div>`;
  };
  return `<details class="card"><summary><h3 style="display:inline">Spielerstatistik</h3></summary>${table(m.home)}${table(m.away)}<p class="muted">T/V = Tore/Vorlagen, Sch. = Schüsse, Zw. = Zweikämpfe gewonnen/gesamt. Quelle: FotMob</p></details>`;
}

/** Kopf und Ticker eines laufenden Spiels. */
export function renderLiveHead(m: Match, live: LiveMatch | null, season: Season, now: Date): string {
  const h = info(season, m.home);
  const a = info(season, m.away);
  const score = live?.status.score ?? m.score ?? [0, 0];
  const minute = live?.status.finished ? "Abpfiff" : live?.status.minute ?? (m.kickoff ? approxMinute(m.kickoff, now) : "");
  const stamp = live ? `Details: Stand ${esc(berlin(live.updated_at).split(", ")[1] ?? "")} Uhr (FotMob, etwa alle 5 Minuten)` : "Details folgen in wenigen Minuten";
  return `<div class="hero live" style="background:linear-gradient(120deg,${esc(h.color)} 0%,color-mix(in srgb,${esc(h.color)} 40%,#111) 48%,color-mix(in srgb,${esc(a.color)} 40%,#111) 52%,${esc(a.color)} 100%)">
    <div class="fx"><div class="t">${crest(h, 44)}<span>${esc(h.short)}</span></div><div class="mid"><div class="livebadge">${live?.status.finished ? "ENDE" : "LIVE"} <span>${esc(minute)}</span></div><div class="score" style="font-size:48px">${score[0]}:${score[1]}</div></div><div class="t">${crest(a, 44)}<span>${esc(a.short)}</span></div></div>
    <div class="tlab" style="text-align:center">Stand und Tore: OpenLigaDB, etwa jede Minute · ${stamp}</div></div>`;
}

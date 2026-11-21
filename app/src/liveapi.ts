import type { Goal, LiveMatch, Match } from "./data";
import { loadJson } from "./data";

const OLDB = "https://api.openligadb.de/getmatchdata/bl1";

interface OldbGoal { matchMinute: number | null; scoreTeam1: number; scoreTeam2: number; goalGetterName: string | null; isPenalty: boolean; isOwnGoal: boolean }
interface OldbMatch { matchID: number; matchIsFinished: boolean; goals: OldbGoal[] | null; matchResults: { resultTypeID: number; pointsTeam1: number; pointsTeam2: number }[] | null }

/** Live-Stand aus OpenLigaDB (direkt vom Handy, etwa minütlich aktuell): Tore der Reihe nach, Torschützen, beendet ja/nein. */
export function mergeOldb(matches: Match[], raw: OldbMatch[]): Match[] {
  const by = new Map(raw.map((r) => [r.matchID, r]));
  return matches.map((m) => {
    const r = by.get(m.id);
    if (!r) return m;
    let h = 0;
    let a = 0;
    const goals: Goal[] = [];
    for (const g of [...(r.goals ?? [])].sort((x, y) => (x.scoreTeam1 + x.scoreTeam2) - (y.scoreTeam1 + y.scoreTeam2))) {
      const team = g.scoreTeam1 > h ? m.home : m.away;
      h = g.scoreTeam1;
      a = g.scoreTeam2;
      goals.push({ minute: g.matchMinute, team, scorer: g.goalGetterName ?? "", penalty: !!g.isPenalty, own_goal: !!g.isOwnGoal });
    }
    const final = r.matchResults?.find((x) => x.resultTypeID === 2);
    const score: [number, number] = r.matchIsFinished && final ? [final.pointsTeam1, final.pointsTeam2] : [h, a];
    return { ...m, score, goals: goals.length ? goals : m.goals, finished: r.matchIsFinished || m.finished };
  });
}

export async function fetchOldb(season: number, md: number): Promise<OldbMatch[] | null> {
  try {
    const res = await fetch(`${OLDB}/${season}/${md}`, { cache: "no-cache" });
    return res.ok ? ((await res.json()) as OldbMatch[]) : null;
  } catch {
    return null;
  }
}

/** Live-Datei des Spiels: auf GitHub Pages direkt aus dem Repository (ohne Wartezeit auf die Veröffentlichung), sonst lokal. */
const cache = new Map<number, { at: number; data: LiveMatch | null }>();
const MIN_GAP_MS = 110_000; // GitHub erlaubt ohne Anmeldung 60 Abrufe pro Stunde: höchstens alle knapp 2 Minuten

export async function fetchLive(id: number): Promise<LiveMatch | null> {
  const hit = cache.get(id);
  if (hit && Date.now() - hit.at < MIN_GAP_MS) return hit.data;
  const data = await fetchLiveNow(id);
  cache.set(id, { at: Date.now(), data });
  return data;
}

async function fetchLiveNow(id: number): Promise<LiveMatch | null> {
  const host = location.hostname;
  if (host.endsWith(".github.io")) {
    const owner = host.split(".")[0];
    const repo = location.pathname.split("/").filter(Boolean)[0];
    try {
      const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/data/live/${id}.json?ref=main`, {
        headers: { Accept: "application/vnd.github.raw+json" }, cache: "no-cache",
      });
      if (res.ok) return (await res.json()) as LiveMatch;
    } catch {
      /* fällt auf die veröffentlichte Kopie zurück */
    }
  }
  return loadJson<LiveMatch>(`live/${id}.json`);
}

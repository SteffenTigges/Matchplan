// Typen der JSON-Dateien, die der Datenjob schreibt (pipeline/matchplan_data/update.py).

export interface TeamInfo { name: string; short: string; color: string; crest: string }
export interface Season { season: number; current_matchday: number; updated_at: string; teams: Record<string, TeamInfo> }

export interface TableRow {
  rank: number; team: string; played: number; won: number; draw: number; lost: number;
  goals: number; against: number; diff: number; points: number; form: ("S" | "U" | "N")[];
}
export interface Table { updated_at: string; rows: TableRow[] }

export interface Goal { minute: number | null; team: string; scorer: string; penalty: boolean; own_goal: boolean }
export interface Match {
  id: number; kickoff: string | null; home: string; away: string; finished: boolean;
  score: [number, number] | null; halftime: [number, number] | null; goals: Goal[];
}
export interface Matchday { matchday: number; matches: Match[] }

export interface Player { id: string; name: string; photo: string | null }
export interface Slot { player: Player; alternatives: Player[] }
export interface Missing { name: string; kind: string; note: string }
export interface TeamLineup {
  team: string; formation: string; rows: Slot[][]; missing: Missing[];
  updated_label: string | null; opponent: string | null; home: boolean | null; fetched_at: string;
}
export interface Lineups { matchday: number; fetched_at: string; teams: Record<string, TeamLineup> }

export interface HistoryEvent { at: string; team: string; kind: string; text: string }
export interface History { matchday: number; events: HistoryEvent[] }

/** Lädt eine Datei aus data/. Fehlt sie oder ist sie kaputt, kommt null zurück. */
export async function loadJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/${path}`, { cache: "no-cache" });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

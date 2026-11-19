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

// --- FotMob-Spielstatistik (data/fotmob/<id>.json) ---
export type StatValue = number | { n: number; pct: number } | null;
export interface Shot {
  team: string | null; player: string | null; min: number | null; x: number | null; y: number | null;
  xg: number | null; xgot: number | null; situation: string | null; type: string | null;
  result: "goal" | "saved" | "miss" | "blocked" | "post"; own_goal: boolean;
}
export interface LineupPlayer { id?: number | null; name: string; pos_id: number | null; rating: number | null; captain: boolean; x: number | null; y: number | null }
export interface FmLineup { team: string | null; formation: string | null; rating: number | null; players: LineupPlayer[] }
export interface FotmobMatch {
  fm_id: number;
  stats: Record<string, [StatValue, StatValue]>;
  shots: Shot[];
  momentum: [number, number][] | null;
  zones: { home: Record<"left" | "center" | "right", number>; away: Record<"left" | "center" | "right", number> } | null;
  lineups: { home: FmLineup; away: FmLineup } | null;
  players: Record<string, unknown>[];
}

// --- Saisonwerte (data/teamstats.json) ---
export interface MetricDef { key: string; label: string; category: string; higher_is_better: boolean; fmt: string; approx: boolean }
export interface TeamStats {
  updated_at: string; categories: string[]; metrics: MetricDef[];
  teams: Record<string, Record<string, { value: number | null; rank: number | null } | number>>;
}

// --- Spieler (data/players.json, data/players/<id>.json) ---
export interface PlayerRow { id: number; name: string; team: string | null; team_name?: string | null; pos: string | null; age: number | null; minutes: number; apps: number; rating: number | null }
export interface PlayerIndex { updated_at: string; players: PlayerRow[] }
export interface PlayerStat { group: string; key: string; title: string; value: number | null; per90: number | null; pct: number | null; fmt?: string }
export interface CareerEntry { team: string; start: string | null; end: string | null; apps: number | null; goals: number | null; kind: string | null }
export interface PlayerProfile {
  id: number; name: string; team: string | null; team_name: string | null; birth_date: string | null; age: number | null;
  height_cm: number | null; foot: string | null; country: string | null; shirt: number | null; market_value: number | null;
  contract_end: string | null; positions: { label: string; short: string; main: boolean }[]; stats: PlayerStat[];
  career: { senior: CareerEntry[]; youth: CareerEntry[]; national: CareerEntry[]; national_youth: CareerEntry[] };
  transfers: { from: string; to: string; date: string | null; fee: string | null; loan: boolean }[]; fetched_at: string;
}

// --- Prognose (data/predictions/<spieltag>.json, data/model.json) ---
export interface Scorer { name: string; li_id: string | null; fm_id: number | null; photo: string | null; minutes: number; lam: number; p: number }
export interface AbsenceInfo { name: string; fm_id: number | null; xg_share: number; minutes_share: number }
export interface Prediction {
  home: string; away: string; kickoff: string | null; made_at: string;
  xg: [number, number]; probs: [number, number, number]; tip: [number, number]; tip_prob: number;
  matrix: number[][];
  markets: { over25: number; btts: number; home_clean_sheet: number; away_clean_sheet: number };
  odds: { home: number; draw: number; away: number; source: string } | null;
  scorers: { home: Scorer[]; away: Scorer[] };
  xi: { home: { li_id: string | null; name: string }[]; away: { li_id: string | null; name: string }[] };
  why: {
    attack: [number, number]; defence: [number, number]; xgf: [number, number]; xga: [number, number]; n: [number, number];
    form: [number | null, number | null]; means: [number, number]; rho: number;
    absence_factor: [[number, number], [number, number]];
    absences: { home: AbsenceInfo[]; away: AbsenceInfo[] };
  };
  lineup_hits?: { home: number | null; away: number | null };
}
export interface Predictions { matchday: number; updated_at: string; matches: Record<string, Prediction> }
export interface ModelCheck {
  updated_at: string;
  calibration: { home: number; away: number; rho: number; matches: number; seasons: string | null; fetched_at: string | null };
  check: {
    matches: number; tendency_rate: number | null; exact_rate: number | null; brier: number | null;
    odds_matches: number; brier_model_same: number | null; brier_odds: number | null;
    by_matchday: { md: number; matches: number; tendency: number; exact: number; brier: number }[];
  };
}

// --- Gegner-Bericht (data/scouting/<team>.json) ---
export interface Evidence { label: string; value: number; fmt: string; rank?: number }
export interface Finding { key?: string; text: string; evidence: Evidence[] }
export interface SituationRow { goals: number; xg: number; shots: number; share: number }
export type Situations = Record<"Spielaufbau" | "Konter" | "Standard" | "Elfmeter", SituationRow>;
export interface Zones { left: number; center: number; right: number }
export interface KeyPlayer { id: number; name: string; pos: string | null; minutes: number; goals: number; assists: number; rating: number | null; xg90: number; xa90: number; why: string[] }
export interface ScoutReport {
  team: string; matches: number; fotmob_matches: number;
  idea: { formations: { formation: string; games: number }[]; tags: Finding[] };
  next: { id: number; home: string; away: string; kickoff: string | null; tip: [number, number] | null; probs: [number, number, number] | null } | null;
  strengths: Evidence[]; weaknesses: Evidence[]; matchplan: Finding[]; findings: Finding[];
  buildup: { metrics: Evidence[]; zones: Zones | null };
  scoring: { situations: Situations | null; bands: number[]; goals: number; inside_box: number | null; metrics: Evidence[] };
  conceding: { situations: Situations | null; bands: number[]; goals: number; opp_zones: Zones | null; metrics: Evidence[] };
  setpieces: { metrics: Evidence[]; goals_for: number | null; goals_against: number | null; corners_against: number | null };
  key_players: KeyPlayer[];
  lines: Partial<Record<"Abwehr" | "Mittelfeld" | "Angriff", { id: number; name: string; rating: number; minutes: number }>>;
  load: { id: number; name: string; minutes: number; full: boolean }[];
  absences: { name: string; kind: string; note: string }[];
  reaction: {
    ht_lead: { games: number; points: number }; ht_draw: { games: number; points: number }; ht_trail: { games: number; points: number };
    points_from_behind: number; points_dropped: number; late_for: number; late_against: number; goals_for: number; goals_against: number;
  };
}

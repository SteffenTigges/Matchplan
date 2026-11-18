# Phase 3 – Spieldaten: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Full statistics for every finished Bundesliga match (momentum, team stats in categories, shot map with xG, attacking zones, line-ups with formation and player ratings) and a team profile with season values and league rank per metric — all from FotMob.

**Architecture:** FotMob pages embed their data as JSON in `<script id="__NEXT_DATA__">`. One league page lists all 306 matches with FotMob ids; one page per finished match holds its statistics. The job fetches the league page every run and only match pages it has not stored yet (or finished < 48 h ago), reduces each to a compact JSON, and computes season aggregates + ranks. The app gets an analysis view per finished match and categories with ranks on the team page.

**Tech Stack:** unchanged.

**Spec:** `docs/superpowers/specs/2026-11-18-matchplan-design.md` (§5 FotMob, §6.2 Spielanalyse, §6.3 Teamprofil, §6.6, §7 xPunkte, §10.3). Laufdaten von bundesliga.com sind **nicht** Teil dieser Phase (eigener Schritt 3b).

## Global Constraints

- FotMob league page: `https://www.fotmob.com/leagues/54/fixtures/bundesliga`; match page: `https://www.fotmob.com` + `pageUrl` from the league data (drop the `#…` fragment).
- Data comes only from `__NEXT_DATA__`; a page without it or with a changed structure is a failed source (status entry), previous files stay.
- Polite: 2 s between requests (existing `get()`), match pages only when missing or finished < 48 h ago. First run fetches ~81 pages once.
- Stored per match: numbers only (no texts, no images). Player photos are not part of this phase.
- Every value shown names its source "FotMob"; derived values ("Näherung") say so.
- Ranks: 1 = best of 18; direction per metric fixed in `METRICS`.
- Legend: technical terms only (xG, xGOT, xA, PPDA, Field Tilt, xPunkte, Großchance, Momentum, Note).

## Review Focus

1. A match page that lacks a section (e.g. no shotmap, no momentum, lineup missing) still produces a match file with the other sections; the app hides the missing section. (Task 1 `test_missing_sections_are_none`, Task 4 `hides_missing_sections`.)
2. Percent strings like `'366 (80%)'` and number strings like `'2.23'` parse to numbers; `None` stays `None`. (Task 1 `test_parses_count_and_percent`.)
3. FotMob ↔ OpenLigaDB matching by matchday + home + away keys; an unmatched FotMob match is skipped and logged, never attached to the wrong game. (Task 3 `test_unmatched_fotmob_match_is_skipped`.)
4. Team with fewer played matches (postponed game): per-game averages divide by that team's own count. (Task 2 `test_averages_use_own_match_count`.)
5. Ranks with ties share the better rank (1, 1, 3). (Task 2 `test_ties_share_rank`.)

---

## File Structure

```
pipeline/matchplan_data/
  teams.py        + fotmob_id per team
  fotmob.py       next_data(html), parse_league(data), parse_match(data) -> dict
  teamstats.py    METRICS, aggregate(matches) -> dict, ranks, xpoints
  update.py       + FotMob step
pipeline/tests/fixtures/fotmob_league.json, fotmob_match.json   (synthetic, reduced __NEXT_DATA__ structures)
pipeline/tests/test_fotmob.py, test_teamstats.py, test_update.py (+FotMob)
data/fotmob/<oldb match id>.json        compact match stats
data/teamstats.json                      {updated_at, matches_counted, teams{key:{metric:{value, rank}}}}
app/src/views/analysis.ts                renderAnalysis(...) for finished matches
app/src/views/teamstats.ts               renderTeamStats(...) categories with ranks
```

FotMob team ids: FCB 9823, BVB 9789, RBL 178475, VFB 10269, TSG 8226, B04 8178, SCF 8358, SGE 9810, FCA 8406, M05 9905, FCU 8149, BMG 9788, HSV 9790, KOE 8722, SVW 8697, S04 10189, SVE 8232, SCP 8460.

---

### Task 1: FotMob parsing

**Files:** `teams.py` (+`fotmob_id`, `team_by_fotmob`), `fotmob.py`, fixtures, `test_fotmob.py`.

**Produces:**
- `next_data(html: str) -> dict | None`
- `parse_league(data: dict) -> list[dict]` → `{"fm_id": int, "url": str, "round": int, "home": key, "away": key, "finished": bool, "kickoff": str}`
- `parse_match(data: dict) -> dict` →
  ```
  {"fm_id", "stats": {key: [home, away]} (numbers; "x (y%)" → {"n": x, "pct": y}),
   "shots": [{"team", "player", "min", "x", "y", "xg", "xgot", "situation", "type", "result": "goal|saved|miss|blocked|post", "own_goal"}],
   "momentum": [[minute, value], ...] | None,
   "zones": {"home": {"left","center","right"}, "away": {...}} | None,
   "lineups": {"home": {"formation","rating","players":[{"name","pos_id","rating","minutes","x","y","captain"}]}, "away": ...} | None,
   "players": [{"team","name","minutes","rating","goals","assists","xg","xa","shots","key_passes","touches_box","tackles","interceptions","recoveries","duels_won","duels_lost"}]}
  ```
  Stats keys kept: BallPossesion, expected_goals, expected_goals_open_play, expected_goals_set_play, expected_goals_on_target, total_shots, ShotsOnTarget, shots_inside_box, blocked_shots, big_chance, big_chance_missed_title, passes, accurate_passes, own_half_passes, opposition_half_passes, long_balls_accurate, accurate_crosses, touches_opp_box, corners, Offsides, matchstats.headers.tackles (→ `tackles`), interceptions, shot_blocks, clearances, keeper_saves, duel_won, ground_duels_won, aerials_won, dribbles_succeeded, fouls, yellow_cards, red_cards.

- [ ] Step 1 tests: `test_next_data_extracts_json`, `test_parse_league_maps_teams_and_rounds`, `test_parses_count_and_percent` (`'366 (80%)'` → `{"n":366,"pct":80}`, `'2.23'` → 2.23), `test_parses_shots_with_xg_and_result`, `test_parses_lineups_with_formation_and_ratings`, `test_missing_sections_are_none`.
- [ ] Step 2–4 RED → implement → GREEN. Step 5 commit `feat(pipeline): FotMob league and match parsing`.

### Task 2: Season aggregates and ranks

**Files:** `teamstats.py`, `test_teamstats.py`.

**Produces:** `METRICS: list[Metric]` (`key, label, category, higher_is_better, fmt`) in the 10 prototype categories (Allgemein, Offensive, Schüsse, Passspiel & Aufbau, Defensive, Gegen den Ball, Standards, Zweikämpfe & Disziplin, Glück & Effizienz); `aggregate(matches: list[tuple[dict, dict]], results) -> dict[key, dict[metric, float]]` (pairs of OpenLigaDB match + FotMob match); `rank(values: dict[key, float], higher_is_better) -> dict[key, int]`; `xpoints(shots_home_xg: list[float], shots_away_xg: list[float]) -> tuple[float, float]` (exact Poisson-binomial over shot xGs, 3/1/0 points).
Derived metrics: `field_tilt = touches_opp_box / (own + opp)`, `ppda = opp own_half_passes / (tackles + interceptions + fouls)` labelled "PPDA (Näherung)", `xg_per_shot`, `goals_minus_xg`, `against_minus_xga`, `points_minus_xpoints`, `clean_sheets`.
- [ ] Tests: `test_xpoints_certain_goal` (home [0.99]*3 vs away [] → home ≈ 3, away ≈ 0), `test_xpoints_symmetric_split`, `test_averages_use_own_match_count`, `test_ties_share_rank`, `test_lower_is_better_ranks_smallest_first`, `test_metrics_cover_all_categories`.
- [ ] RED → GREEN → commit `feat(pipeline): season aggregates, ranks and xPoints`.

### Task 3: Update job integration

**Files:** `update.py`, `test_update.py`.
Steps in `run_update` after OpenLigaDB: fetch league page → `parse_league` → for each finished FotMob match find the OpenLigaDB match (same matchday, home, away); skip and log unmatched; fetch the match page if `data/fotmob/<id>.json` is missing or the match finished < 48 h ago → write. Then `aggregate` over all stored files → `data/teamstats.json`. Status key `"fotmob"`.
- [ ] Tests (fake fetcher with the two fixtures): `test_writes_fotmob_match_and_teamstats`, `test_stored_old_match_is_not_refetched`, `test_unmatched_fotmob_match_is_skipped`, `test_fotmob_down_keeps_previous_files`.
- [ ] RED → GREEN → commit; push branch; Actions run green; log shows `fotmob` OK and the number of stored matches (expected 81 on first run).

### Task 4: Match analysis view

**Files:** `app/src/data.ts` (+types), `app/src/views/analysis.ts` + test, `views/spiele.ts` (finished match page uses it), `main.ts` (load `fotmob/<id>.json`).
**Produces:** `renderAnalysis(m: Match, fm: FotmobMatch | null, season: Season): string` — sections in this order, each hidden when its data is missing:
1. Momentum (SVG area chart, home up / away down, goal markers from OpenLigaDB goals),
2. Statistics in categories (Überblick, Schüsse, xG, Passspiel, Defensive, Zweikämpfe, Disziplin) as two-sided bars (better side highlighted),
3. Shot map (both teams on one pitch, circle size = xG, goals highlighted, legend line),
4. Attacking zones (left/centre/right per team),
5. Line-ups (formation, players with rating chips coloured like the prototype; top-3 ratings listed).
- [ ] Tests: `renders_xg_and_possession`, `shotmap_scales_circles_by_xg`, `hides_missing_sections`, `rating_colours_match_scale`, `momentum_path_has_one_point_per_minute`.
- [ ] RED → GREEN → commit `feat(app): match analysis`.

### Task 5: Team profile with ranks

**Files:** `app/src/views/teamstats.ts` + test, `views/teams.ts`, `main.ts` (load `teamstats.json`).
**Produces:** `renderTeamStats(key: string, stats: TeamStats): string` — category jump bar + collapsible categories (first three open), each row: label, value (formatted per metric), rank chip (green ≤ 4, red ≥ 13), "Näherung" tag for PPDA; footer "Daten: FotMob · {n} Spiele".
- [ ] Tests: `renders_all_categories`, `rank_chip_colours`, `marks_approximations`. RED → GREEN → commit `feat(app): team stats with league ranks`.

### Task 6: Legend and finish

- [ ] Extend `legend.ts` with: xG, xGOT, xA, Großchance, PPDA, Field Tilt, xPunkte, Momentum, Note (rating scale), Perzentil not yet. Tests: `legend_explains_xg_when_present`, `legend_skips_absent_terms`.
- [ ] Browser check with generated data (real fixtures) for `#spiel/<finished id>` and `#team/<key>`, light + dark, phone width; no console errors, no horizontal scroll.
- [ ] Commit, push, final review, PR.

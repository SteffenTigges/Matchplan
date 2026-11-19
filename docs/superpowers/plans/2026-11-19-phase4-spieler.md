# Phase 4 – Spieler: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A profile for every Bundesliga player who has played this season: photo, bio (age, height, foot, nation, market value, contract), season stats with per-90 values and percentiles against players of the same position, career from youth club to today (incl. national teams), transfers — plus a searchable player list and links from line-ups and team pages.

**Architecture:** FotMob player pages embed everything in `__NEXT_DATA__` (`props.pageProps.data`: `playerInformation`, `careerHistory.careerItems{senior,youth,national team,national team youth}`, `transfers`, `firstSeasonStats.statsSection` with `per90` and `percentileRankPer90`, `positionDescription`, `traits`). Players are discovered from the stored FotMob match files (line-ups and player stats, now with FotMob player ids). The job fetches at most 40 player pages per run, oldest first, refreshing each at most every 7 days.

**Tech Stack:** unchanged.

**Spec:** `docs/superpowers/specs/2026-11-18-matchplan-design.md` §6.4 (Spielerprofil, Karriere), §6.6, §7 (Perzentile), §10.4. Similar players and "Könnte so gut werden wie …" are phase 7.

## Global Constraints

- Player page URL: `https://www.fotmob.com/players/{id}/x` (slug is ignored by FotMob).
- Player photo: `https://images.fotmob.com/image_resources/playerimages/{id}.png`, loaded at runtime, never stored; fallback initials (existing `photo()`).
- Percentiles are FotMob's (`percentileRankPer90`, same-position comparison); shown as 0–100 bars, coloured like the prototype (≥ 80 blue, ≥ 60 green, ≥ 35 orange, else red).
- At most 40 player pages per run; a page counts as fresh for 7 days.
- Match files get `"v": 2` and player ids; files without `v: 2` are refetched once regardless of age (one-time ~81 pages).
- Legend: Perzentil, /90.

## Review Focus

1. Player page without stats section (new signing, keeper with keeper-only stats) → profile still written; app hides the section. (`test_player_without_stats`, `hides_empty_sections`.)
2. Career entries without end date (current club) or without appearances → shown as "seit …"/"–", never "undefined". (`test_career_open_end`, `career_open_end_label`.)
3. More than 40 due players → the 40 oldest/missing are fetched, the rest next run; no crash. (`test_player_fetch_is_capped_and_oldest_first`.)
4. Player who changed club mid-season → team taken from `primaryTeam`; a non-Bundesliga primary team is kept as text, not mapped. (`test_primary_team_outside_bundesliga`.)
5. Search with umlauts/diacritics ("Ljubicic" finds "Ljubičić"). (`search_ignores_diacritics`.)

## Tasks

### Task 1: Player ids in match files
`fotmob.py`: `players[].id` (from `playerStats[*].id`), `lineups.*.players[].id`; `parse_match` result gets `"v": 2`. `update.py`: a stored match file without `v == 2` is refetched regardless of age.
Tests: `test_match_has_player_ids`, `test_old_format_match_is_refetched`.

### Task 2: Player page parsing
`fotmob.py`: `parse_player(data) -> dict` →
`{id, name, team (key|None), team_name, birth_date, age, height_cm, foot, country, market_value, contract_end, shirt, positions:[{label, short, main}], stats:[{group, key, title, value, per90, pct}], traits:{title, items:[{key,title,value}]}, career:{senior:[…], youth:[…], national:[…], national_youth:[…]} (entries {team, start, end, apps, goals, kind}), transfers:[{from, to, date, fee, loan}]}`.
Tests: `test_parses_bio`, `test_parses_stats_with_percentiles`, `test_parses_career_sections`, `test_career_open_end`, `test_player_without_stats`, `test_primary_team_outside_bundesliga`. Fixture: reduced number/name-only structure from the real Asllani page.

### Task 3: Player job
`update.py`: collect player ids from all stored match files (with team + minutes played); due = missing or `fetched_at` older than 7 days; fetch the 40 oldest; write `data/players/<id>.json`; write `data/players.json` index `{updated_at, players:[{id, name, team, pos, age, minutes, rating, apps}]}` (minutes/rating/apps aggregated from match files). Status key `fotmob_players` with note "x von y Profilen aktuell".
Tests: `test_writes_player_profile_and_index`, `test_player_fetch_is_capped_and_oldest_first`, `test_fresh_player_is_not_refetched`.

### Task 4: Player list and profile in the app
Tab "Spieler" (4 tabs). `views/players.ts`: `renderPlayerList(index, season, query, team?)` (search box, results grouped by team, photo, position, rating), `renderPlayer(profile, season, index entry)` — hero in club colour with photo, bio chips; stats by group with value, per-90 and percentile bar; career timeline (youth → senior, national); transfers. Routes `#spieler`, `#spieler/<id>`. Links from analysis line-ups and team page ("Kader" list).
Tests: `search_ignores_diacritics`, `renders_percentile_bars`, `career_open_end_label`, `hides_empty_sections`, `lineup_names_link_to_player`.

### Task 5: Legend, browser check, review, PR.

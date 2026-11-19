# Phase 6 – Scouting & Mein Verein: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An opponent report for every Bundesliga team (5 areas, 12 sections) from the co-trainer's perspective, plus the tab "Mein Verein" as start page: favourite club, next match with tip, the three most important findings about the opponent, tiles into the report, "Wir gegen sie", data sources.

**Architecture:** New `scouting.py` builds `data/scouting/<team>.json` from what is stored (FotMob match files, OpenLigaDB matches with goal minutes and half-time scores, teamstats with ranks, players index/profiles, Ligainsider line-up, predictions). Every finding is rule-based and carries the numbers behind it (`{text, evidence:[{label, value, rank?}]}`). The app gets tabs Mein Verein · Spiele · Teams · Spieler · Scouting (Status moves into "Datenquellen" on Mein Verein, route `#status` stays), views `scouting.ts` and `verein.ts`; the favourite club is stored in the browser (`localStorage`, wrapped in try/catch; without it the page asks for a club).

**Tech Stack:** unchanged.

**Spec:** §6.5, §7 (Gegner-Bericht, Matchplan-Ideen: regelbasiert, jede Aussage mit Zahlen), §10.6.

## Decisions (mine)

- **Report sections** (data available → shown; else a short "keine Daten" line):
  1. Überblick – *Spielidee*: most used formation (+ share), style tags from ranks (Ballbesitz, Field Tilt, PPDA, lange Bälle, Flanken), *Prognose* (next match from predictions), *Stärken & Schwächen*: metrics with rank ≤ 3 / ≥ 16 (max 4 each), *Matchplan*: rule list (below).
  2. Mit Ball – *Spielaufbau*: pass accuracy, share in opponent half, long-ball accuracy, attack sides (Ø left/centre/right from zones), *So treffen sie*: goals and xG by situation (Spielaufbau, Konter, Standard, Elfmeter), by 15-minute band, share from inside the box, top scorers (goals, xG).
  3. Gegen den Ball – *So kassieren sie*: same splits for shots against, *Standards*: xG for/against from set pieces, corners, goals from set pieces.
  4. Personal – *Schlüsselspieler*: top 5 by (xG + xA)/90 and rating with ≥ 450 min, each with the two best percentiles from the profile as "warum"; *Duelle* (only Mein Verein view): per line (Abwehr/Mittelfeld/Angriff) my best player vs theirs by rating; *Personal & Belastung*: absences (Ligainsider), minutes in the last 3 matches per regular (≥ 250 of 270 → "voll belastet").
  5. Spielverlauf – *Reaktion*: points after leading / trailing at half-time, goals scored and conceded 76'+, points won from behind and dropped from ahead (from goal minutes), *Schiedsrichter*: no free source → stated as not available.
- **Situation mapping:** RegularPlay → Spielaufbau, FastBreak → Konter, SetPiece/FromCorner/FreeKick/ThrowInSetPiece → Standard, Penalty → Elfmeter; own goals separate.
- **Matchplan rules** (each fires with evidence; ordered by strength, max 5): set-piece weakness (xga_setplay rank ≥ 13 → "Standards suchen"), late goals conceded share ≥ 30 % → "Druck in der Schlussphase", weak side (shots against from one side ≥ 40 %) → "über links/rechts angreifen", high press (PPDA rank ≤ 4) → "lange Bälle hinter die erste Pressinglinie", low possession (rank ≥ 13) + high counter share for them → "Restverteidigung sichern, Konter verhindern", aerial weakness (aerial_rate rank ≥ 13) → "Flanken und hohe Bälle", leaking big chances (rank ≥ 13) → "Tiefe suchen", strong after half-time trailing → "auch bei Führung nicht zurückziehen".
- **Three key findings** on Mein Verein = the first three matchplan items, fallback strengths.
- **"Wir gegen sie"**: 10 headline metrics side by side with ranks (reusing the two-sided bars).
- Favourite stored only in the viewer's browser; nothing personal leaves the device.

## Review Focus

1. Team with 0 FotMob matches → report file with empty sections, app shows "keine Daten", no crash. (`test_team_without_matches`.)
2. Goal-minute logic for leads: stoppage-time minutes (90+3 stored as 90/93), own goals counted for the right team. (`test_comeback_points_from_goal_order`.)
3. Situation shares sum to 100 % (rounding), own goals separate. (`test_situation_split`.)
4. Matchplan items always carry evidence; no rule fires on missing data. (`test_rules_need_data`.)
5. localStorage unavailable → Mein Verein still renders the club picker. (`picker_without_storage`.)

## Tasks

1. `scouting.py` splits: situations, minute bands, sides, formation usage, set pieces, game-state reaction. Tests: `test_situation_split`, `test_minute_bands`, `test_formation_usage`, `test_comeback_points_from_goal_order`, `test_team_without_matches`.
2. Key players, load, strengths/weaknesses, matchplan rules, findings. Tests: `test_key_players_need_minutes`, `test_strengths_and_weaknesses_from_ranks`, `test_rules_need_data`, `test_rule_evidence_present`, `test_load_last_three`.
3. Job: write `data/scouting/<team>.json` for all 18 teams each run; status `scouting`. Test: `test_writes_report_for_every_team`.
4. App: tabs, routes `#verein`, `#scouting`, `#scouting/<team>`, views. Tests: `report_renders_all_areas`, `missing_section_says_no_data`, `findings_show_evidence`, `picker_without_storage`, `wir_gegen_sie_rows`, `duels_only_in_club_view`.
5. Legend terms if new (none expected besides existing), browser check, review, PR, merge.

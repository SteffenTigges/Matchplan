# Phase 7 – Vergleiche: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On every player profile: "Ähnliche Spieler" (playing style) and, for players up to 24, "Könnte so gut werden wie …" (impact compared with established top players). Style and impact are shown separately.

**Architecture:** New `similar.py` reads all stored player profiles (`data/players/<id>.json`, FotMob percentiles and per-90 values) and writes one file `data/similar.json` `{updated_at, players: {id: {style: [...], could_be: [...]}}}`. The app loads it on the profile page.

**Spec:** §6.4, §7 (Ähnliche Spieler, Könnte so gut werden wie), §10.7.

## Decisions (mine) and limits

- **Style:** cosine similarity of FotMob percentiles centred at 50, over the stat keys both players have (at least 8), same position group (Tor / Abwehr / Mittelfeld / Angriff from the main position). Top 5, shown as "x % ähnlich".
- **Impact ("Könnte so gut werden wie …")**: players aged ≤ 24 with ≥ 450 minutes. Compared with **today's** top players aged 25–30 of the same group (top 10 % by average FotMob rating, ≥ 900 minutes). Impact values per 90: Angriff/Mittelfeld xG, xA, Torchancen vorbereitet, Ballaktionen im gegn. Strafraum; Abwehr: abgefangene Bälle, Ballgewinne, Zweikämpfe gewonnen, angekommene Pässe. Score = mean of min(young/top, 1.2) → "erreicht schon x % der Wirkung". Top 3 with score ≥ 60 %.
- **Not possible with free sources:** earlier seasons at the same age (Understat in maintenance since phase 1, FotMob pages hold only the current season's per-90 values) and players from other leagues (would need thousands of extra page fetches). The app states this under the section. If FotMob career entries carry per-season rows, `parse_player` keeps them as `seasons` for a later upgrade.
- Comparison set = Bundesliga players with a stored profile.

## Review Focus
1. Fewer than 8 shared keys → pair skipped. (`test_needs_shared_keys`.)
2. Different position groups never compared. (`test_same_group_only`.)
3. Player over 24 → no "could be". (`test_could_be_only_young`.)
4. Missing per-90 value in a top player → that key skipped, not counted as 0. (`test_missing_impact_value_skipped`.)

## Tasks
1. `similar.py` + tests above + `test_style_identical_is_100`.
2. Job: write `similar.json`; status `vergleiche`. Test `test_writes_similar_file`.
3. App: profile sections; tests `renders_similar_players`, `could_be_hidden_for_old_players`, `explains_limits`.
4. Browser check, review, PR, merge.

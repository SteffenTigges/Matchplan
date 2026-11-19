# Phase 5 – Prognose: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A prediction for every upcoming Bundesliga match (most likely result, win/draw/loss chances, expected goals, all results 0:0–5:5, markets, "Warum?", bookmaker cross-check, goal probability per player in the predicted line-up, "Wer trifft?") plus an ongoing model check against finished matchdays — all computed by the data job, shown in the app.

**Architecture:** New `predict.py` (pure functions: strengths, Dixon-Coles matrix, tip, markets, scorers, absences, model check) and `odds.py` (football-data.co.uk CSV: upcoming odds from `fixtures.csv`, past results + closing odds from `D1.csv` of this and the three previous seasons for calibration). The job writes `data/predictions/<md>.json` for the current matchday (a match's prediction is frozen at kick-off and kept), `data/model.json` (calibration + model check). The app reads them on the matchday list, the match page, a new route `#prognose/<id>` and the status page.

**Tech Stack:** unchanged.

**Spec:** §6.2 (Prognoseseite, Alle Ergebnisse, Wer trifft?, Abgleich offizielle Aufstellung), §7 (Ergebnisprognose, Modellprüfung, Torschützen-Wahrscheinlichkeit), §10.5.

## Decisions (mine)

- **No running data (phase 3b dropped):** bundesliga.com publishes a TDM policy (`tdm-reservation: 1`, permission only with `obtainConsent`). Like Transfermarkt it is not harvested. "Physis" stays empty.
- **No Elo:** ClubElo has been down (502) since phase 1. Cross-check uses bookmaker odds only; the card says so.
- **Strength:** attack = xG for per game, defence = xG against per game, each 70 % season + 30 % last five matches, shrunk toward the league mean with weight n/(n+4) (n = matches played). λ_home = μ_home · att_h · def_a, λ_away = μ_away · att_a · def_h, att/def relative to league mean. μ_home/μ_away from the league's goals per game this season, blended with the calibration seasons while n < 10.
- **Calibration:** home/away goal means and Dixon-Coles ρ by maximum likelihood (grid ρ ∈ [−0.20, 0.05], step 0.01) on the three previous seasons' results (football-data D1). Refreshed at most every 7 days; on failure the previous `model.json` values stay; without any, defaults μ_home 1.70, μ_away 1.35, ρ −0.05.
- **Absences (Näherung):** absent players (Ligainsider "Es fehlen") matched to FotMob players of the team. Attack: λ_own × (1 − 0.5 · Σ xG share of absent players), Defence: λ_opp × (1 + 0.10 · Σ minutes share of absent players among the team's minutes), both capped at 25 %.
- **Scorers:** expected minutes starter 80, a slot with "oder" alternative splits 50/50 (starter 45, alternative 35); per player λ_p = λ_team · 0.97 · share · min/90 where share = player xG per 90 / team xG per game, players with < 270 minutes use position priors (Sturm 0.22, Mittelfeld 0.08, Abwehr 0.03, Tor 0); Σλ_p normalised to ≤ 0.97 · λ_team. P = 1 − exp(−λ_p). Penalty xG is part of the player's xG, so penalty takers are already weighted up.
- **Tip:** most likely exact result within the most likely outcome (home/draw/away).
- **Model check:** walk-forward for every finished match: predict from matches of earlier matchdays only (no absences), record tendency hit, exact hit, 3-way Brier score; same Brier for bookmaker closing odds where available. Shown as "Modellprüfung".
- **Line-up check:** the predicted XI per team is stored in the prediction at kick-off; after the match it is compared to FotMob's starting XI ("Ligainsider lag bei 9 von 11 richtig").

## Global Constraints

- football-data URLs: `https://www.football-data.co.uk/fixtures.csv` (all leagues, filter `Div == "D1"`), `https://www.football-data.co.uk/mmz4281/{yy}{yy+1}/D1.csv`. Columns used: Date, HomeTeam, AwayTeam, FTHG, FTAG, AvgH/AvgD/AvgA (fallback B365H/D/A). CSV may start with BOM.
- Team names: mapping table in `teams.py` (`fd_name`); unmatched names are logged, never guessed.
- Implied probabilities: 1/odds normalised to sum 1.
- Everything derived is labelled "Näherung" or with its inputs (Rechenweg).
- Legend: Dixon-Coles, Brier-Score, Über/Unter 2,5, Implizite Wahrscheinlichkeit, λ.

## Review Focus

1. Matrix sums to 1 (± 1e-9) incl. Dixon-Coles correction; probabilities never negative for ρ in grid. (`test_matrix_sums_to_one`, `test_dixon_coles_never_negative`.)
2. Team with 0 finished FotMob matches (season start) → league mean, no division by zero. (`test_strength_without_matches_is_league_mean`.)
3. Prediction for a match that has kicked off is never overwritten. (`test_started_match_prediction_is_frozen`.)
4. Model check uses only earlier matchdays (no leakage). (`test_walk_forward_uses_only_earlier_matchdays`.)
5. Ligainsider name ↔ FotMob player matching with diacritics and short names; unmatched player gets the position prior, not a crash. (`test_matches_player_by_slug`, `test_unmatched_player_gets_prior`.)
6. Missing odds (no fixtures.csv row / site down) → prediction still written, odds null, app hides cross-check. (`test_odds_missing_keeps_prediction`, `hides_odds_when_missing`.)

## Tasks

### Task 1: Model core (`predict.py`)
`score_matrix(lh, la, rho, n=10)`, `outcome_probs(m)`, `tip(m)`, `markets(m)` (over 2.5, both score, clean sheets), `strengths(history, team)` with 70/30 + shrinkage, `expected_goals(home, away, strengths, means)`, `fit_calibration(results)` (μ_home, μ_away, ρ).
Tests: `test_matrix_sums_to_one`, `test_dixon_coles_never_negative`, `test_tip_is_within_most_likely_outcome`, `test_markets_from_matrix`, `test_strength_without_matches_is_league_mean`, `test_recent_form_weighs_30_percent`, `test_calibration_recovers_home_advantage` (synthetic results).

### Task 2: Odds and calibration data (`odds.py`, `teams.py`)
`parse_csv(text)`, `upcoming_odds(rows)`, `results(rows)`, `fd_name` for all 18 teams (verified against the real fixtures.csv/D1.csv headers in the Actions log). Fixture: small synthetic CSV with BOM.
Tests: `test_parses_csv_with_bom`, `test_implied_probabilities_sum_to_one`, `test_unknown_team_is_skipped`, `test_fallback_to_b365`.

### Task 3: Absences and scorers
`match_player(li_player, fm_players)` (slug tokens vs normalised FotMob names, same team), `absence_factors(...)`, `scorers(lineup, player_season, lam)`.
Tests: `test_matches_player_by_slug`, `test_unmatched_player_gets_prior`, `test_alternative_splits_minutes`, `test_scorer_lambdas_do_not_exceed_team`, `test_absence_factor_capped`.

### Task 4: Job integration and model check
`update.py`: after FotMob/players: calibration (≤ every 7 days) → odds → per current-matchday match not yet kicked off: prediction (+ predicted XI ids/names); kicked-off ones keep the stored entry; after the match `lineup_hits` from FotMob starters. `model.json`: calibration, check {matches, tendency_rate, exact_rate, brier, brier_odds, by_matchday}. Status keys `prognose`, `quoten`.
Tests: `test_writes_predictions_for_current_matchday`, `test_started_match_prediction_is_frozen`, `test_walk_forward_uses_only_earlier_matchdays`, `test_odds_missing_keeps_prediction`, `test_lineup_hits_after_match`.

### Task 5: App views
Matchday list: tip, three-part chance bar, most likely scorer. Upcoming match page: prognosis hero card (tip, sentence, expected goals, chances), "Warum?" (attack/defence/form/home/personnel bars), "Gegencheck" (bookmaker), button → `#prognose/<id>` (all results sorted, 6×6 table, markets), pitch with goal % per player, "Wer trifft?" list, "Rechenweg" details. Finished match: "Prognose war …" + line-up hits. Status page: Modellprüfung.
Tests: `renders_tip_and_chances`, `all_results_sorted_desc`, `hides_odds_when_missing`, `pitch_shows_goal_probability`, `finished_match_shows_prior_prediction`, `model_check_card`.

### Task 6: Legend, browser check (real data), final review, PR, merge.

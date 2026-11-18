# Phase 2 – Grunddaten: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Real Bundesliga 2026/27 data in the app: fixtures, results with scorers, table with form, and Ligainsider's predicted lineups (with photos, alternatives, absences and a week-long change history), shown in the tabs "Spiele" and "Teams".

**Architecture:** The Python job gains three sources: OpenLigaDB (JSON API), Ligainsider (HTML parser) and a snapshot-diff that turns successive Ligainsider fetches into change events. `python -m matchplan_data.update` writes small JSON files under `data/`; the existing workflow runs it on a denser schedule and commits on `main`. The app becomes a hash-routed shell with tabs Spiele · Teams · Status; every screen is a pure `render…(data) → HTML` function with Vitest tests on fixture data.

**Tech Stack:** unchanged from phase 1 (Python 3.12 + requests + pytest; TypeScript 5.6 + Vite 5.4 + Vitest 2.1).

**Spec:** `docs/superpowers/specs/2026-11-18-matchplan-design.md` (§3 Bilder, §5 Quellen, §6.2/6.3/6.6, §7 Wochen-Verlauf, §8, §10.2)

## Global Constraints

- Season 2026 (= 2026/27), league `bl1`. OpenLigaDB base `https://api.openligadb.de`.
- Images are never committed; the app loads them from `cdn.ligainsider.de` at runtime and shows a colour crest / initials when an image fails (`onerror`).
- Polite fetching: ≥ 2 s between requests to the same host, timeout 30 s, one fetch per page per run.
- A source that fails leaves its previous file untouched; `data/status/sources.json` records per source `{ok, at, error}`.
- All displayed times in Europe/Berlin. All user-facing text German.
- App paths stay relative (`base: "./"`); GitHub Pages path is `/Matchplan/`.
- Legend explains only technical terms/abbreviations present on the page (positions, formation notation); no basics.
- Design tokens, fonts and component look follow the prototype (`https://claude.ai/artifact/JS3tLSDvn9gqivBjkh12aR`): club-colour hero cards, shield crests, cards with 16 px radius, bottom tab bar.

## Review Focus

1. Ligainsider page without lineup (season break, layout change, Adblock page): parser returns `None`, previous lineup file stays, status records the error — app keeps showing the last good lineup with its timestamp. (Task 2 `test_page_without_lineup_returns_none`, Task 4 `test_failed_lineup_keeps_previous_file`.)
2. Same lineup fetched twice: no change events, no history growth. (Task 3 `test_identical_snapshots_produce_no_events`.)
3. Postponed/unscheduled match (no kickoff, or not finished after its kickoff): shown as "Termin offen" / without score, never as 0:0. (Task 1 `test_unfinished_match_has_no_score`, Task 6 `renders_open_kickoff`.)
4. Player photo or crest URL 404: fallback crest/initials, layout unchanged. (Task 7 `photo_has_fallback_handler`.)
5. Matchday rollover: "current matchday" is the first matchday with an unfinished match; after the last game of a matchday finishes, the next one becomes current and the lineup history starts fresh for it. (Task 1 `test_current_matchday_is_first_with_unfinished_match`, Task 3 `test_history_is_per_matchday`.)

---

## File Structure

```
pipeline/matchplan_data/
  teams.py          TEAMS registry (18 clubs: key, OpenLigaDB id, Ligainsider URL, short name, colour)
  openligadb.py     fetch + transform: matches, table, form, current matchday
  ligainsider.py    parse_lineup_page(html) -> TeamLineup | None
  history.py        diff_lineups(old, new) -> list[Event]; append_history(...)
  update.py         orchestrator CLI: writes data/*.json, status
  probe.py          (unchanged)
pipeline/tests/
  fixtures/openligadb_md9.json, openligadb_md10.json, openligadb_table.json, ligainsider_bmg.html
  test_openligadb.py, test_ligainsider.py, test_history.py, test_update.py
data/
  season.json                 {season, current_matchday, updated_at, teams{key:{name,short,color,crest}}}
  table.json                  {updated_at, rows[{rank,team,played,won,draw,lost,goals,against,diff,points,form[]}]}
  matchdays/<n>.json          {matchday, matches[{id,kickoff,home,away,finished,score,halftime,goals[]}]}
  lineups/current.json        {matchday, fetched_at, teams{key: TeamLineup}}
  lineups/history-<n>.json    {matchday, events[{at,team,kind,text}]}
  status/sources.json         {source:{ok,at,error}}
app/src/
  data.ts           types + loadJson<T>(path) (null on 404/network error)
  router.ts         parseRoute(hash) -> Route
  ui.ts             esc(), crest(team, size), photo(url, name), berlin(date)
  legend.ts         legendFor(html) -> string
  views/spiele.ts   renderMatchday(), renderMatch()
  views/teams.ts    renderTable(), renderTeam()
  views/lineup.ts   renderPitch(), renderMissing(), renderHistory()
  views/status.ts   (moved from src/status.ts)
  main.ts           shell: header, tab bar, route → view
```

---

### Task 1: Team registry and OpenLigaDB transform

**Files:** Create `pipeline/matchplan_data/teams.py`, `pipeline/matchplan_data/openligadb.py`, fixtures `openligadb_md9.json` (2 finished matches of matchday 9 incl. one own goal and one penalty, trimmed from the live API), `openligadb_md10.json` (2 unfinished matches, one with kickoff in the past and `matchIsFinished: false`), `openligadb_table.json` (3 rows). Test `pipeline/tests/test_openligadb.py`.

**Interfaces – Produces:**
- `@dataclass(frozen=True) class Team: key: str; name: str; short: str; oldb_id: int; li_url: str; color: str`; `TEAMS: list[Team]` (18, keys: `FCB BVB RBL VFB TSG B04 SCF SGE FCA M05 FCU BMG HSV KOE SVW S04 SVE SCP`); `team_by_oldb(id) -> Team`; `team_by_name(name) -> Team` (exact full name as on Ligainsider/OpenLigaDB).
  Colours and Ligainsider URLs from the 18.11.2026 run (`/fc-bayern-muenchen/1/`, `/borussia-dortmund/14/`, `/rb-leipzig/1311/`, `/vfb-stuttgart/12/`, `/tsg-hoffenheim/10/`, `/bayer-04-leverkusen/4/`, `/sc-freiburg/18/`, `/eintracht-frankfurt/3/`, `/fc-augsburg/21/`, `/1-fsv-mainz-05/17/`, `/1-fc-union-berlin/1246/`, `/borussia-moenchengladbach/5/`, `/hamburger-sv/9/`, `/1-fc-koeln/15/`, `/sv-werder-bremen/2/`, `/fc-schalke-04/13/`, `/sv-07-elversberg/1331/`, `/sc-paderborn-07/1249/`); OpenLigaDB ids `40 7 1635 16 175 6 112 91 95 81 80 87 100 65 134 9 198 31`.
- `transform_matches(raw: list[dict]) -> list[dict]` → `{"id", "kickoff" (UTC ISO or None), "home" key, "away" key, "finished" bool, "score" [h,a] | None, "halftime" [h,a] | None, "goals": [{"minute","team" key,"scorer","penalty","own_goal"}]}`; score from `resultTypeID == 2`, halftime from `resultTypeID == 1`.
- `current_matchday(matchdays: dict[int, list[dict]]) -> int` — smallest matchday with an unfinished match, else 34.
- `transform_table(raw: list[dict], matches: list[dict]) -> list[dict]` → rows with `rank` (list order), team key, counts, `form`: last 5 finished results of that team, oldest first, as `"S"|"U"|"N"`.

- [ ] **Step 1: Write failing tests**
```python
def test_finished_match_has_score_and_goals():
    m = transform_matches(load("openligadb_md9.json"))[0]
    assert m["home"] == "BVB" and m["away"] == "SVE" and m["score"] == [2, 1] and m["halftime"] == [0, 0]
    assert m["goals"][2] == {"minute": 81, "team": "SVE", "scorer": "N. Futkeu", "penalty": False, "own_goal": False}
def test_unfinished_match_has_no_score():
    m = transform_matches(load("openligadb_md10.json"))[0]
    assert m["finished"] is False and m["score"] is None
def test_current_matchday_is_first_with_unfinished_match():
    assert current_matchday({9: transform_matches(load("openligadb_md9.json")), 10: transform_matches(load("openligadb_md10.json"))}) == 10
def test_table_rows_have_keys_and_form():
    rows = transform_table(load("openligadb_table.json"), transform_matches(load("openligadb_md9.json")))
    assert rows[0]["team"] == "FCB" and rows[0]["points"] == 21 and rows[0]["rank"] == 1
    assert rows[1]["team"] == "BVB" and rows[1]["form"] == ["S"]
def test_registry_has_18_unique_teams():
    assert len(TEAMS) == 18 and len({t.oldb_id for t in TEAMS}) == 18
```
- [ ] **Step 2:** `pytest -q pipeline/tests/test_openligadb.py` → FAIL (ImportError).
- [ ] **Step 3:** Implement `teams.py`, `openligadb.py` (pure functions; fetching lives in `update.py`).
- [ ] **Step 4:** Same command → 5 passed.
- [ ] **Step 5:** Commit `feat(pipeline): team registry and OpenLigaDB transforms`.

---

### Task 2: Ligainsider parser

**Files:** Create `pipeline/matchplan_data/ligainsider.py`; fixture `pipeline/tests/fixtures/ligainsider_bmg.html` (the `<title>` plus the section from `VORAUSSICHTLICHE AUFSTELLUNG` to the end of the "fehlen" list of the 18.11.2026 Gladbach page, scripts/ads stripped, < 60 KB); test `pipeline/tests/test_ligainsider.py`.

**Interfaces – Produces:**
- `@dataclass class Player: id: str; name: str; photo: str | None` (`id` = Ligainsider slug, e.g. `david-herold_34927`)
- `@dataclass class Slot: player: Player; alternatives: list[Player]`
- `@dataclass class TeamLineup: team: str (full name); formation: str; rows: list[list[Slot]]; missing: list[dict] ({"name","kind","note"}); updated_label: str | None; opponent: str | None; home: bool | None`
- `parse_lineup_page(html: str) -> TeamLineup | None` — rows from keeper to attack, columns in Ligainsider order; `formation` = row lengths without the keeper joined by "-"; soft hyphens removed from notes.

- [ ] **Step 1: Write failing tests**
```python
def test_parses_gladbach_lineup():
    lu = parse_lineup_page(fixture("ligainsider_bmg.html"))
    assert lu.team == "Borussia Mönchengladbach" and lu.formation == "3-4-3" and lu.home is True
    assert sum(len(r) for r in lu.rows) == 11 and lu.rows[0][0].player.name == "Nicolas"
    herold = lu.rows[2][3]
    assert herold.player.id == "david-herold_34927" and herold.player.photo.endswith("david-herold-gladbach-2627.jpg")
    assert [a.name for a in herold.alternatives] == ["Castrop"]
def test_parses_missing_players():
    lu = parse_lineup_page(fixture("ligainsider_bmg.html"))
    assert lu.missing[0] == {"name": "Kō Itakura", "kind": "Gelb-Rote Karte", "note": "Sperre"}
    assert "­" not in "".join(m["note"] for m in lu.missing)
def test_page_without_lineup_returns_none():
    assert parse_lineup_page("<html><title>Adblocker erkannt</title></html>") is None
```
- [ ] **Step 2:** FAIL (ImportError). **Step 3:** implement (port of `parse_li.py` from the 18.11. trial, extended by photo + id). **Step 4:** 3 passed. **Step 5:** Commit `feat(pipeline): Ligainsider lineup parser`.

---

### Task 3: Lineup change history

**Files:** Create `pipeline/matchplan_data/history.py`; test `pipeline/tests/test_history.py`.

**Interfaces – Consumes:** `TeamLineup`, `Slot`, `Player` (Task 2). **Produces:**
- `diff_lineups(team_key: str, old: TeamLineup | None, new: TeamLineup, at: str) -> list[dict]` events `{"at","team","kind","text"}`, kinds and exact texts:
  - `first`: `"Erste Prognose: {formation}"` (old is None)
  - `formation`: `"Formation {old} → {new}"`
  - `in`: `"{name} rückt in die Startelf"`; `out`: `"{name} nicht mehr in der Startelf"` (compare sets of starter ids)
  - `alt`: `"Offen: {starter} oder {alt1}/{alt2}"` for a starter whose alternatives went from empty to non-empty
  - `missing`: `"Fällt aus: {name} ({kind})"` for names new in `missing`; `back`: `"Wieder dabei: {name}"` for names gone from `missing`
- `append_history(path: Path, matchday: int, events: list[dict]) -> None` — file per matchday `history-<n>.json`, events appended, never rewritten.

- [ ] **Step 1: Failing tests:** `test_first_snapshot_yields_first_event`, `test_identical_snapshots_produce_no_events`, `test_player_swap_yields_in_and_out` (assert both texts exactly), `test_new_absence_and_return` , `test_history_is_per_matchday` (append to md 10 then md 11 → two files, md 10 unchanged).
- [ ] **Step 2–4:** RED → implement → 5 passed. **Step 5:** Commit `feat(pipeline): lineup change history`.

---

### Task 4: Update orchestrator and schedule

**Files:** Create `pipeline/matchplan_data/update.py`; modify `.github/workflows/data.yml`; test `pipeline/tests/test_update.py`.

**Interfaces – Consumes:** Tasks 1–3, `probe.http_fetch` / `Response`. **Produces:** `run_update(out: Path, fetch: Fetcher, now: datetime, sleep=time.sleep) -> dict` (returns the status dict) and CLI `python -m matchplan_data.update --out data`.
Order: OpenLigaDB matchdays 1–34 (`/getmatchdata/bl1/2026/{n}`, only matchdays not yet fully finished in the existing file plus the current one; first run fetches all) → table (`/getbltable/bl1/2026`) → Ligainsider 18 pages → diff against previous `lineups/current.json` → write files. Lineups are stored as dicts (`dataclasses.asdict`) and read back into dataclasses for diffing.

- [ ] **Step 1: Failing tests** with a fake fetcher keyed by URL serving the fixtures:
  - `test_writes_season_table_matchdays_and_lineups` (all files exist; `season.json["current_matchday"] == 10`; `lineups/current.json["teams"]["BMG"]["formation"] == "3-4-3"`; crest URL for BMG `https://cdn.ligainsider.de/images/teams/medium/borussia-moenchengladbach-wappen.png`)
  - `test_failed_lineup_keeps_previous_file` (second run where BMG page returns 500 → BMG lineup unchanged, `status["ligainsider:BMG"]["ok"] is False`)
  - `test_second_identical_run_adds_no_history`
- [ ] **Step 2–4:** RED → implement → 3 passed; full `pytest -q pipeline` green.
- [ ] **Step 5:** `data.yml`: add step `python -m matchplan_data.update --out data` after the probe; commit `data/` (not only `probe.json`) on main with the existing rebase/retry loop; add `timeout-minutes: 20`. Schedule (UTC): `17 5,16 * * 1-4`, `17 9-21 * * 5,6,0` (hourly Fri–Sun, covers 75 min before kickoffs within an hour). Keep `workflow_dispatch`.
- [ ] **Step 6:** Commit `feat(pipeline): update job for fixtures, table and lineups`; push branch; verify the Actions run is green and its log shows 18 lineups parsed.

---

### Task 5: App shell, routing, shared UI

**Files:** Create `app/src/data.ts`, `app/src/router.ts`, `app/src/ui.ts`; move `src/status.ts` → `src/views/status.ts` (+ test); rewrite `app/src/main.ts`, `app/src/style.css` (prototype tokens), `app/index.html` (header + `<nav class="tabs">`). Tests `router.test.ts`, `ui.test.ts`.

**Interfaces – Produces:**
- `type Route = {view:"spiele", matchday?:number} | {view:"spiel", id:number} | {view:"teams"} | {view:"team", key:string} | {view:"status"}`; `parseRoute(hash: string): Route` (`""`/unknown → `{view:"spiele"}`; `#spiele/12`, `#spiel/83228`, `#teams`, `#team/BMG`, `#status`).
- `loadJson<T>(path: string): Promise<T | null>`; types `Season, TableRow, Match, Goal, TeamLineup, Slot, Player, HistoryEvent` mirroring the JSON of Task 4.
- `esc(s)`, `berlin(iso) -> "Sa. 21.11., 15:30"`, `crest(team: {short,color,crest}, size) -> string` (img with onerror → shield SVG with initial), `photo(url, name, size) -> string` (img with onerror → initials circle).
- [ ] Tests: `parses_all_routes`, `berlin_formats_weekday_date_time`, `crest_falls_back_on_error` (output contains `onerror`), `photo_has_fallback_handler`. RED → implement → green → commit `feat(app): shell with tabs, routing and shared UI`.

---

### Task 6: Spiele (matchday list and match page)

**Files:** `app/src/views/spiele.ts` + test.
**Produces:** `renderMatchday(md: number, matches: Match[], season: Season): string` (prev/next arrows, one card per match: crests, short names, Berlin kickoff or score, "Termin offen" when kickoff is null); `renderMatch(match, season, lineups | null, history | null): string` (hero in both club colours, score/halftime, goal list with minute, scorer, "Elfmeter"/"Eigentor"; for unfinished matches the lineup section from Task 7).
- [ ] Tests: `renders_score_for_finished_match`, `renders_open_kickoff`, `renders_goal_markers_for_penalty_and_own_goal`, `links_to_match_page`. RED → green → commit `feat(app): Spiele tab`.

---

### Task 7: Lineup components

**Files:** `app/src/views/lineup.ts` + test.
**Produces:** `renderPitch(home: TeamLineup, away: TeamLineup, homeTeam, awayTeam): string` (SVG pitch as in the prototype's live view: home bottom, away top, player photos in circles via `<image>` with `onerror` fallback, name under/over the dot, alternatives "oder …" in amber, staggered labels for 5-player rows, edge labels anchored inward); `renderMissing(team, lineup)`; `renderHistory(events: HistoryEvent[], teams)` (timeline as prototype "Verlauf der Woche", newest last, "Stand: …" footer).
- [ ] Tests: `pitch_contains_all_22_names`, `pitch_marks_alternatives`, `photo_has_fallback_handler`, `history_lists_events_in_order`, `missing_shows_kind_and_note`. RED → green → commit `feat(app): lineup pitch, absences and weekly history`.

---

### Task 8: Teams (table and team page)

**Files:** `app/src/views/teams.ts` + test.
**Produces:** `renderTable(rows, season)` (rank, crest, short name, form squares S/U/N, points; favourite star not yet); `renderTeam(key, season, rows, matches: Match[], lineups | null)` (hero in club colour with rank and points, next match card, predicted lineup of this team only as a list grouped by row, absences, season results).
- [ ] Tests: `table_has_18_rows_in_rank_order` (fixture with 18 rows), `form_squares_render_letters`, `team_page_shows_next_match_and_absences`. RED → green → commit `feat(app): Teams tab`.

---

### Task 9: Legend and wiring

**Files:** `app/src/legend.ts` + test; `main.ts` wiring of all routes.
**Produces:** `legendFor(html: string): string` — entries only for terms present: positions (TW, IV, LV, RV, ZM, LM, RM, DM, ZOM, LA, RA, ST), formation notation (`/\d-\d-\d/`), "Alternative" marker. Same visual as prototype.
- [ ] Tests: `legend_lists_formation_when_present`, `legend_empty_when_no_terms`. RED → green.
- [ ] Wire routes in `main.ts`; `npm test`, `npx vite build`; serve `dist` locally under `/Matchplan/` with `data/` copied and check with Playwright that `#spiele`, `#spiel/<id of a matchday-10 match>`, `#teams`, `#team/BMG`, `#status` render without console errors.
- [ ] Commit `feat(app): legend and routing`; push; open PR to `main` (user merges).

# Phase 1 – Machbarkeit: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that every planned data source is reachable from GitHub Actions, and ship an installable, empty PWA on GitHub Pages that shows the result of that check.

**Architecture:** A small Python package (`pipeline/`) contains a source probe. A GitHub Actions workflow runs it on a schedule and on push, writes `data/status/probe.json` and commits it back. A Vite/TypeScript app (`app/`) is built by a second workflow, gets `data/` copied in, and is deployed to GitHub Pages. The app's only screen in this phase is "Quellen-Check".

**Tech Stack:** Python 3.12, requests 2.32, pytest 8 · Node 22, TypeScript 5.6, Vite 5.4, Vitest 2.1 · GitHub Actions, GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-11-18-matchplan-design.md` (sections 3, 4, 5, 8.2, 9, 10.1)

## Global Constraints

- Cost 0 €: no paid APIs, no paid services, only GitHub Free features.
- Repository is public; Pages URL is `https://steffentigges.github.io/matchplan/` → Vite `base: '/matchplan/'`.
- Every HTML page carries `<meta name="robots" content="noindex, nofollow">`.
- No images and no raw scraped pages committed, except trimmed parser test fixtures (none needed in this phase).
- Polite fetching: at most one request per source per probe run, ≥ 2 s pause between requests, timeout 30 s.
- App language German; app texts as given in the tasks.
- Status data lives in `data/status/`.

## Review Focus

1. A source that hangs or throws must not abort the probe; it is recorded as failed with the error text, and the other sources still run. (Task 1 test `test_exception_is_recorded_not_raised`.)
2. A source that answers 200 with a consent/captcha/blocked page counts as failed, not OK: each target has a content check. (Task 1 test `test_status_200_without_marker_fails`.)
3. App opened before any probe has run (no `probe.json`, or 404): shows "Noch kein Abruf gelaufen." instead of an error. (Task 3 test `renders_empty_state_when_no_report`.)
4. Old probe data: the screen shows the probe time and marks it "veraltet" when older than 36 h. (Task 3 test `marks_report_older_than_36h_as_stale`.)
5. Assets under the Pages sub-path: build output references `/matchplan/…`, not `/…`. (Task 3 Step "verify build paths".)

---

## File Structure

```
pipeline/
  pyproject.toml                 package "matchplan-data", deps: requests; dev: pytest
  matchplan_data/__init__.py
  matchplan_data/probe.py        ProbeTarget, ProbeResult, run_probe(), TARGETS, main()
  tests/test_probe.py
.github/workflows/data.yml       test + probe + commit data/status/probe.json
.github/workflows/pages.yml      build app, copy data/, deploy to Pages
app/
  package.json, tsconfig.json, vite.config.ts
  index.html                     noindex, manifest link, #app root
  public/manifest.webmanifest, public/icon-192.png, public/icon-512.png, public/sw.js
  src/main.ts                    fetch data/status/probe.json → render
  src/status.ts                  renderStatus(report, now) → HTML string
  src/status.test.ts
  src/style.css
data/status/.gitkeep
```

---

### Task 1: Source probe core

**Files:**
- Create: `pipeline/pyproject.toml`, `pipeline/matchplan_data/__init__.py`, `pipeline/matchplan_data/probe.py`
- Test: `pipeline/tests/test_probe.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Response: status: int; text: str; content_type: str; elapsed_ms: int`
  - `Fetcher = Callable[[str], Response]`
  - `@dataclass(frozen=True) class ProbeTarget: key: str; name: str; url: str; check: Callable[[Response], bool]; purpose: str`
  - `@dataclass class ProbeResult: key: str; name: str; url: str; ok: bool; status: int | None; elapsed_ms: int | None; bytes: int | None; error: str | None; purpose: str`
  - `run_probe(targets: list[ProbeTarget], fetch: Fetcher, pause_s: float = 2.0, sleep: Callable[[float], None] = time.sleep) -> list[ProbeResult]`
  - `http_fetch(url: str) -> Response` (requests, timeout 30 s, desktop-browser User-Agent, `Accept-Language: de-DE,de;q=0.9`)

- [ ] **Step 1: Write the failing tests** in `pipeline/tests/test_probe.py`

```python
def ok_target(check=lambda r: "MARK" in r.text):
    return ProbeTarget("x", "X", "https://x.test", check, "Test")

def test_ok_when_status_200_and_marker_present():
    res = run_probe([ok_target()], lambda u: Response(200, "..MARK..", "text/html", 12), sleep=lambda s: None)
    assert res[0].ok is True and res[0].status == 200 and res[0].bytes == 8 and res[0].error is None

def test_status_200_without_marker_fails():
    res = run_probe([ok_target()], lambda u: Response(200, "Bitte Cookies akzeptieren", "text/html", 5), sleep=lambda s: None)
    assert res[0].ok is False and res[0].error == "Inhalt unerwartet"

def test_non_200_fails_with_status_in_error():
    res = run_probe([ok_target()], lambda u: Response(403, "MARK", "text/html", 5), sleep=lambda s: None)
    assert res[0].ok is False and res[0].error == "HTTP 403"

def test_exception_is_recorded_not_raised():
    def boom(u): raise TimeoutError("timed out")
    res = run_probe([ok_target(), ok_target()], boom, sleep=lambda s: None)
    assert len(res) == 2 and all(r.ok is False for r in res)
    assert res[0].error == "TimeoutError: timed out" and res[0].status is None

def test_pauses_between_requests_not_after_last():
    slept = []
    run_probe([ok_target()] * 3, lambda u: Response(200, "MARK", "text/html", 1), pause_s=2.0, sleep=slept.append)
    assert slept == [2.0, 2.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pipeline && pip install -e '.[dev]' && pytest -q`
Expected: FAIL (ImportError: cannot import name 'run_probe')

- [ ] **Step 3: Implement** the dataclasses, `run_probe` and `http_fetch` in `pipeline/matchplan_data/probe.py`. `pyproject.toml`: `requires-python = ">=3.12"`, dependencies `requests>=2.32,<3`, optional `dev = ["pytest>=8,<9"]`. A check that raises counts as "Inhalt unerwartet".

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pipeline && pytest -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add pipeline
git commit -m "feat(pipeline): add source probe core"
```

---

### Task 2: Probe targets, report file and workflow

**Files:**
- Modify: `pipeline/matchplan_data/probe.py` (add `TARGETS`, `build_report`, `main`)
- Test: `pipeline/tests/test_probe.py`
- Create: `.github/workflows/data.yml`, `data/status/.gitkeep`

**Interfaces:**
- Consumes: Task 1 types and `run_probe`, `http_fetch`.
- Produces:
  - `TARGETS: list[ProbeTarget]`, exactly these keys in this order, with these URLs and checks:

| key | name | url | check |
|---|---|---|---|
| `openligadb` | OpenLigaDB | `https://api.openligadb.de/getmatchdata/bl1/2026` | JSON list, len ≥ 1 |
| `fotmob_api` | FotMob (API) | `https://www.fotmob.com/api/leagues?id=54` | `'"table"' in text` |
| `fotmob_web` | FotMob (Webseite) | `https://www.fotmob.com/leagues/54/overview/bundesliga` | `'__NEXT_DATA__' in text` |
| `understat` | Understat | `https://understat.com/league/Bundesliga/2026` | `'teamsData' in text` |
| `bundesliga` | bundesliga.com | `https://www.bundesliga.com/en/bundesliga/stats/players` | `'Distance covered' in text or 'distance' in text` |
| `ligainsider` | Ligainsider | `https://www.ligainsider.de/borussia-moenchengladbach/5/` | `text.count('player_position_row') >= 4` |
| `ligainsider_img` | Ligainsider (Bilder) | `https://cdn.ligainsider.de/images/teams/small/fc-bayern-muenchen-wappen.png` | `content_type.startswith('image/')` |
| `transfermarkt` | Transfermarkt | `https://www.transfermarkt.de/bundesliga/startseite/wettbewerb/L1` | `'Bundesliga' in text and 'captcha' not in text.lower()` |
| `clubelo` | ClubElo | `http://api.clubelo.com/Bayern` | `text.startswith('Rank,Club')` |
| `footballdata` | football-data.co.uk | `https://www.football-data.co.uk/mmz4281/2627/D1.csv` | `text.startswith('Div,')` |

  - `build_report(results: list[ProbeResult], now: datetime) -> dict` → `{"checked_at": now ISO-8601 with offset, "ok_count": int, "total": int, "sources": [asdict(r) …]}`
  - `main(argv: list[str] | None = None) -> int`: `python -m matchplan_data.probe --out PATH` writes the report (UTF-8, indent 2, `ensure_ascii=False`), prints one line per source, returns 0 even when sources fail.

- [ ] **Step 1: Write the failing tests**

```python
def test_targets_cover_all_spec_sources():
    assert [t.key for t in TARGETS] == ["openligadb","fotmob_api","fotmob_web","understat","bundesliga",
                                         "ligainsider","ligainsider_img","transfermarkt","clubelo","footballdata"]

def test_ligainsider_check_needs_lineup_rows():
    t = next(t for t in TARGETS if t.key == "ligainsider")
    assert t.check(Response(200, 'class="player_position_row"' * 4, "text/html", 1))
    assert not t.check(Response(200, "<html>Adblocker erkannt</html>", "text/html", 1))

def test_build_report_counts_and_serializes():
    now = datetime(2026, 11, 18, 17, 0, tzinfo=timezone.utc)
    r = [ProbeResult("a","A","u",True,200,5,10,None,"p"), ProbeResult("b","B","u",False,None,None,None,"HTTP 403","p")]
    rep = build_report(r, now)
    assert rep["checked_at"] == "2026-11-18T17:00:00+00:00" and rep["ok_count"] == 1 and rep["total"] == 2
    assert rep["sources"][1]["error"] == "HTTP 403"

def test_main_writes_report(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "http_fetch", lambda u: Response(500, "", "text/html", 1))
    monkeypatch.setattr(probe.time, "sleep", lambda s: None)
    out = tmp_path / "probe.json"
    assert probe.main(["--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["total"] == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd pipeline && pytest -q`
Expected: FAIL (ImportError: TARGETS)

- [ ] **Step 3: Implement** `TARGETS`, `build_report`, `main` (argparse, `--out` required, parent dirs created).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd pipeline && pytest -q`
Expected: 9 passed

- [ ] **Step 5: Write `.github/workflows/data.yml`**
  - Triggers: `push` on any branch with paths `pipeline/**` and `.github/workflows/data.yml`; `workflow_dispatch`; `schedule: cron '17 5,17 * * *'` (fires only on the default branch).
  - `permissions: contents: write`; `concurrency: data` (no parallel runs).
  - Steps: checkout → setup-python 3.12 → `pip install -e 'pipeline[dev]'` → `pytest -q pipeline` → `python -m matchplan_data.probe --out data/status/probe.json` → append a Markdown table of the results to `$GITHUB_STEP_SUMMARY` → commit `data/status/probe.json` as `github-actions[bot]` with message `data: Quellen-Check` and push to the same branch only if it changed.

- [ ] **Step 6: Commit, push, and read the result**

```bash
git add pipeline .github/workflows/data.yml data/status/.gitkeep
git commit -m "feat(pipeline): probe all data sources from GitHub Actions"
git push -u origin <branch>
```
Then open the workflow run (GitHub MCP `actions_list` / `get_job_logs`).
Expected: job green; `data/status/probe.json` committed on the branch with 10 sources. The OK/failed count is **the phase-1 result**; record it in the hand-off message, per source.

---

### Task 3: App skeleton with "Quellen-Check" screen

**Files:**
- Create: `app/package.json`, `app/tsconfig.json`, `app/vite.config.ts`, `app/index.html`, `app/src/main.ts`, `app/src/status.ts`, `app/src/style.css`, `app/public/manifest.webmanifest`, `app/public/sw.js`, `app/public/icon-192.png`, `app/public/icon-512.png`
- Test: `app/src/status.test.ts`

**Interfaces:**
- Consumes: report JSON shape from Task 2 (`checked_at`, `ok_count`, `total`, `sources[] {key,name,url,ok,status,elapsed_ms,bytes,error,purpose}`).
- Produces: `export type ProbeReport`, `export function renderStatus(report: ProbeReport | null, now: Date): string`.

- [ ] **Step 1: Write the failing tests** in `app/src/status.test.ts`

```ts
const base = { checked_at: "2026-11-18T17:00:00+00:00", ok_count: 1, total: 2, sources: [
  { key:"openligadb", name:"OpenLigaDB", url:"u", ok:true, status:200, elapsed_ms:120, bytes:5000, error:null, purpose:"Spielplan" },
  { key:"transfermarkt", name:"Transfermarkt", url:"u", ok:false, status:403, elapsed_ms:80, bytes:0, error:"HTTP 403", purpose:"Karrieren" } ] };

test("renders_empty_state_when_no_report", () => {
  expect(renderStatus(null, new Date())).toContain("Noch kein Abruf gelaufen.");
});
test("shows_ok_count_and_each_source", () => {
  const html = renderStatus(base, new Date("2026-11-18T18:00:00Z"));
  expect(html).toContain("1 von 2 Quellen erreichbar");
  expect(html).toContain("OpenLigaDB"); expect(html).toContain("HTTP 403");
});
test("marks_report_older_than_36h_as_stale", () => {
  expect(renderStatus(base, new Date("2026-11-20T06:00:01Z"))).toContain("veraltet");
  expect(renderStatus(base, new Date("2026-11-20T04:59:59Z"))).not.toContain("veraltet");
});
test("escapes_source_text", () => {
  const evil = { ...base, sources: [{ ...base.sources[1], error: "<img src=x>" }] };
  expect(renderStatus(evil, new Date())).not.toContain("<img src=x>");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd app && npm install && npx vitest run`
Expected: FAIL (cannot find module './status')

- [ ] **Step 3: Implement**
  - `status.ts`: the card list in the prototype's style (green/red dot, name, purpose, status, time in ms), heading "Quellen-Check", line "Stand: <dd.mm.yyyy, hh:mm> Uhr" in Europe/Berlin, "veraltet" chip when older than 36 h; all source strings HTML-escaped.
  - `main.ts`: `fetch('data/status/probe.json', {cache:'no-store'})`; on 404 or network error → `renderStatus(null, …)`; registers `sw.js`.
  - `sw.js`: cache app shell on install (cache name `matchplan-v1`); network-first for `data/`, cache-first for everything else.
  - `manifest.webmanifest`: name "Matchplan", short_name "Matchplan", `start_url: "/matchplan/"`, `scope: "/matchplan/"`, `display: "standalone"`, theme `#0a1120`, background `#0a1120`, icons 192/512.
  - Icons: pitch-green square with "M" in Barlow Condensed style, rendered to PNG once (e.g. via Playwright screenshot of an inline SVG) and committed.
  - `index.html`: `lang="de"`, robots noindex meta, manifest link, `theme-color`, `apple-mobile-web-app-capable`, `apple-touch-icon` → icon-192.
  - Design tokens and fonts as in the prototype (light/dark via `prefers-color-scheme`).
  - `vite.config.ts`: `base: '/matchplan/'`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd app && npx vitest run`
Expected: 4 passed

- [ ] **Step 5: Verify build paths**

Run: `cd app && npx vite build && grep -o 'src="/matchplan/assets/[^"]*"' dist/index.html`
Expected: one match; no `src="/assets/`.

- [ ] **Step 6: Commit**

```bash
git add app
git commit -m "feat(app): installable PWA skeleton with Quellen-Check screen"
```

---

### Task 4: Pages deployment

**Files:**
- Create: `.github/workflows/pages.yml`

**Interfaces:**
- Consumes: `app/` build (Task 3), `data/` (Task 2).

- [ ] **Step 1: Write `.github/workflows/pages.yml`**
  - Triggers: `push` to `main` with paths `app/**`, `data/**`, `.github/workflows/pages.yml`; `workflow_run` of workflow "data" (type `completed`, branch `main`) because commits by the data job do not trigger push workflows; `workflow_dispatch`.
  - `permissions: contents: read, pages: write, id-token: write`; `concurrency: pages`.
  - Steps: checkout → setup-node 22 → `npm ci` in `app` → `npx vitest run` → `npx vite build` → `cp -r data app/dist/data` → `actions/configure-pages` → `actions/upload-pages-artifact` (path `app/dist`) → `actions/deploy-pages`.

- [ ] **Step 2: Commit and push**

```bash
git add .github/workflows/pages.yml
git commit -m "ci: deploy app to GitHub Pages"
git push
```

- [ ] **Step 3: Hand-off to the user (requires their action)**
  - Settings → Pages → Source: **GitHub Actions**.
  - The branch must reach `main` (merge) for Pages and the schedule to run.
  - After deploy: open `https://steffentigges.github.io/matchplan/` on the phone, "Zum Startbildschirm hinzufügen", check the Quellen-Check screen.
  Expected: the page loads under `/matchplan/`, the icon appears on the home screen, the screen lists 10 sources.

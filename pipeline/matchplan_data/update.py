"""Datenjob: holt Spielplan, Tabelle und Aufstellungen und schreibt die JSON-Dateien für die App."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import probe
from .history import append_history, diff_lineups
from .ligainsider import Player, Slot, TeamLineup, diagnose, parse_lineup_page
from .openligadb import current_matchday, matchday_url, table_url, transform_matches, transform_table
from .probe import Fetcher
from .teams import TEAMS, team_by_key

SEASON = 2026
PAUSE_S = 2.0


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _lineup_from_dict(d: dict) -> TeamLineup:
    p = lambda x: Player(x["id"], x["name"], x.get("photo"))  # noqa: E731
    rows = [[Slot(p(s["player"]), [p(a) for a in s["alternatives"]]) for s in row] for row in d["rows"]]
    return TeamLineup(d["team"], d["formation"], rows, d["missing"], d.get("updated_label"), d.get("opponent"), d.get("home"))


SETTLE = timedelta(hours=48)  # so lange nach dem letzten Anstoß wird ein Spieltag noch nachgeladen


def _settled(matches: list[dict], now: datetime) -> bool:
    if not matches or not all(m["finished"] for m in matches):
        return False
    last = max(m["kickoff"] for m in matches if m.get("kickoff"))
    return now - datetime.fromisoformat(last.replace("Z", "+00:00")) > SETTLE


def _fits(lu: TeamLineup, key: str, match: dict | None) -> bool:
    """Passt die Ligainsider-Aufstellung zum Spiel dieses Spieltags?"""
    if match is None:
        return False
    if lu.home is not None and lu.home != (match["home"] == key):
        return False
    if lu.opponent:
        other = team_by_key(match["away"] if match["home"] == key else match["home"])
        return other.name.startswith(lu.opponent) or lu.opponent.startswith(other.name)
    return True


def run_update(out: Path, fetch: Fetcher, now: datetime, sleep: Callable[[float], None] = time.sleep) -> dict:
    out = Path(out)
    at = now.isoformat(timespec="seconds")
    status: dict[str, dict] = {}
    first_request = [True]

    def get(url: str) -> str:
        if not first_request[0]:
            sleep(PAUSE_S)
        first_request[0] = False
        r = fetch(url)
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return r.text

    # --- OpenLigaDB: Spieltage (offene, frisch beendete und fehlende neu holen) ---
    matchdays: dict[int, list[dict]] = {}
    errors = []
    for md in range(1, 35):
        path = out / "matchdays" / f"{md}.json"
        old = _read(path)
        if old and old.get("season") != SEASON:
            old = None  # Datei einer anderen Saison
        if old and _settled(old["matches"], now):
            matchdays[md] = old["matches"]
            continue
        try:
            matchdays[md] = transform_matches(json.loads(get(matchday_url(SEASON, md))))
            _write(path, {"matchday": md, "season": SEASON, "matches": matchdays[md]})
        except Exception as e:  # alte Datei bleibt stehen
            errors.append(f"Spieltag {md}: {e}")
            matchdays[md] = old["matches"] if old else []
    all_matches = [m for ms in matchdays.values() for m in ms]
    old_season = _read(out / "season.json") or {}
    previous = old_season.get("current_matchday") if old_season.get("season") == SEASON else None
    current = current_matchday(matchdays, now, previous)

    try:
        rows = transform_table(json.loads(get(table_url(SEASON))), all_matches)
        _write(out / "table.json", {"updated_at": at, "rows": rows})
    except Exception as e:
        errors.append(f"Tabelle: {e}")
    status["openligadb"] = {"ok": not errors, "at": at, "error": "; ".join(errors) or None}

    if current is None:  # noch nie Spiele gesehen: nichts Falsches schreiben
        _write(out / "status" / "sources.json", status)
        return status

    _write(out / "season.json", {
        "season": SEASON, "current_matchday": current, "updated_at": at,
        "teams": {t.key: {"name": t.name, "short": t.short, "color": t.color, "crest": t.crest} for t in TEAMS},
    })

    # --- Ligainsider: Aufstellungen + Verlauf ---
    prev = _read(out / "lineups" / "current.json") or {}
    same_matchday = prev.get("matchday") == current and prev.get("season", SEASON) == SEASON
    prev_teams = prev.get("teams", {}) if same_matchday else {}
    teams_out: dict[str, dict] = {}
    events: list[dict] = []
    for t in TEAMS:
        key = f"ligainsider:{t.key}"
        try:
            page = get(t.li_url)
            lu = parse_lineup_page(page)
            if lu is None:
                raise RuntimeError(f"Keine Aufstellung auf der Seite: {diagnose(page)}")
            match = next((m for m in matchdays.get(current, []) if t.key in (m["home"], m["away"])), None)
            if not _fits(lu, t.key, match):
                raise RuntimeError(f"Aufstellung für ein anderes Spiel (gegen {lu.opponent})")
        except Exception as e:
            status[key] = {"ok": False, "at": at, "error": str(e)}
            if t.key in prev_teams:
                teams_out[t.key] = prev_teams[t.key]
            continue
        old = _lineup_from_dict(prev_teams[t.key]) if t.key in prev_teams else None
        events += diff_lineups(t.key, old, lu, at)
        teams_out[t.key] = {**asdict(lu), "fetched_at": at}
        status[key] = {"ok": True, "at": at, "error": None}

    _write(out / "lineups" / "current.json", {"season": SEASON, "matchday": current, "fetched_at": at, "teams": teams_out})
    if events:
        append_history(out / "lineups", current, events, season=SEASON)
    _write(out / "status" / "sources.json", status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aktualisiert Spielplan, Tabelle und Aufstellungen.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    status = run_update(args.out, lambda u: probe.http_fetch(u), datetime.now(timezone.utc), sleep=lambda s: time.sleep(s))
    for k, v in status.items():
        print(f"{'OK  ' if v['ok'] else 'FAIL'} {k:22} {v['error'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

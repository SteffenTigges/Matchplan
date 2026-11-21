"""Liveticker: Spiele, die gerade laufen, alle paar Minuten von FotMob holen (eigener, schneller Workflow)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from . import probe
from .fotmob import LEAGUE_URL, next_data, parse_events, parse_league, parse_match, parse_status

SEASON = 2026
WINDOW = timedelta(minutes=150)  # ab Anpfiff so lange gilt ein Spiel als „läuft gerade“
EARLY = timedelta(minutes=10)


def _read(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def due_matches(out: Path, now: datetime) -> list[dict]:
    """Spiele des aktuellen und des nächsten Spieltags, deren Anpfiff im Zeitfenster liegt."""
    season = _read(out / "season.json") or {}
    md = season.get("current_matchday")
    if not md:
        return []
    found = []
    for d in (md - 1, md, md + 1):
        for m in (_read(out / "matchdays" / f"{d}.json") or {}).get("matches", []):
            if not m.get("kickoff"):
                continue
            k = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00"))
            if k - EARLY <= now <= k + WINDOW:
                found.append({**m, "matchday": d})
    return found


def run_live(out: Path, fetch: probe.Fetcher, now: datetime) -> dict:
    """Schreibt data/live/<id>.json und data/live/index.json. Rückgabe: {'live': n, 'finished_now': [ids]}."""
    out = Path(out)
    due = due_matches(out, now)
    at = now.isoformat(timespec="seconds")
    index = _read(out / "live" / "index.json") or {"matches": {}}
    result = {"live": 0, "finished_now": [], "errors": []}
    if not due:
        return result
    r = fetch(LEAGUE_URL)
    league = parse_league(next_data(r.text) or {}) if r.status == 200 else []
    by_teams = {(f["round"], f["home"], f["away"]): f for f in league}
    for m in due:
        f = by_teams.get((m["matchday"], m["home"], m["away"]))
        if not f:
            result["errors"].append(f"{m['home']}–{m['away']}: nicht bei FotMob gefunden")
            continue
        try:
            rr = fetch(f"https://www.fotmob.com/match/{f['fm_id']}")
            nd = next_data(rr.text) if rr.status == 200 else None
            if not nd:
                raise RuntimeError(f"HTTP {rr.status}")
            st = parse_status(nd)
            full = parse_match(nd)
            data = {"id": m["id"], "fm_id": f["fm_id"], "home": m["home"], "away": m["away"], "kickoff": m["kickoff"],
                    "updated_at": at, "status": st, "events": parse_events(nd),
                    "stats": full["stats"], "momentum": full["momentum"], "shots": full["shots"], "zones": full["zones"],
                    "lineups": full["lineups"], "players": full["players"]}
            _write(out / "live" / f"{m['id']}.json", data)
            was = (index["matches"].get(str(m["id"])) or {}).get("finished", False)
            index["matches"][str(m["id"])] = {"started": st["started"], "finished": st["finished"], "minute": st["minute"],
                                               "score": st["score"], "updated_at": at}
            if st["started"] and not st["finished"]:
                result["live"] += 1
            if st["finished"] and not was:
                result["finished_now"].append(m["id"])
        except Exception as e:
            result["errors"].append(f"{m['home']}–{m['away']}: {e}")
    index["updated_at"] = at
    _write(out / "live" / "index.json", index)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Liveticker-Daten aktualisieren.")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    res = run_live(a.out, lambda u: probe.http_fetch(u), datetime.now(timezone.utc))
    print(f"live={res['live']} finished_now={res['finished_now']} errors={res['errors']}")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as fh:
            fh.write(f"finished={'1' if res['finished_now'] else '0'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

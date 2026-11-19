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
from .forecast import run_forecast
from .fotmob import FORMAT_VERSION, LEAGUE_URL, next_data, parse_league, parse_match, parse_player, player_url
from .history import append_history, diff_lineups
from .ligainsider import Player, Slot, TeamLineup, diagnose, parse_lineup_page
from .teamstats import aggregate, build_teamstats
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


SETTLE = timedelta(hours=48)
RETRY_INCOMPLETE = timedelta(days=14)  # unvollständige FotMob-Seiten so lange erneut versuchen
CORE_STATS = {"expected_goals", "passes", "total_shots"}
PLAYER_CAP = 40  # Spielerseiten pro Lauf
PLAYER_FRESH = timedelta(days=7)  # so lange nach dem letzten Anstoß wird ein Spieltag noch nachgeladen


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


def _update_fotmob(out: Path, get: Callable[[str], str], matchdays: dict[int, list[dict]], now: datetime, at: str, status: dict) -> None:
    """FotMob-Spielstatistik für beendete Spiele holen (nur fehlende oder frisch beendete) und Saisonwerte rechnen."""
    by_teams = {(md, m["home"], m["away"]): m for md, ms in matchdays.items() for m in ms}
    by_id = {m["id"]: m for ms in matchdays.values() for m in ms}
    errors: list[str] = []
    unmatched = 0
    try:
        data = next_data(get(LEAGUE_URL))
        if data is None:
            raise RuntimeError("Keine eingebetteten Daten auf der Ligaseite")
        fixtures = parse_league(data)
    except Exception as e:
        errors.append(f"Ligaseite: {e}")
        fixtures = []
    for fm in fixtures:
        if not fm["finished"]:
            continue
        om = by_teams.get((fm["round"], fm["home"], fm["away"]))
        if om is None:
            unmatched += 1
            continue
        path = out / "fotmob" / f"{om['id']}.json"
        kickoff = datetime.fromisoformat((fm["kickoff"] or "1970-01-01T00:00:00Z").replace("Z", "+00:00"))
        if path.exists() and now - kickoff > SETTLE:
            old = _read(path) or {}
            current_format = old.get("v") == FORMAT_VERSION
            complete = bool(old.get("stats")) and bool(old.get("shots"))
            if current_format and (complete or now - kickoff > RETRY_INCOMPLETE):
                continue
        try:
            nd = next_data(get(fm["url"]))
            if nd is None:
                raise RuntimeError("Keine eingebetteten Daten")
            parsed = parse_match(nd)
            if parsed["fm_id"] != fm["fm_id"]:
                raise RuntimeError(f"Seite zeigt ein anderes Spiel ({parsed['fm_id']})")
            _write(path, {**parsed, "oldb_id": om["id"], "matchday": fm["round"], "season": SEASON})
        except Exception as e:  # alte Datei bleibt stehen
            errors.append(f"{fm['home']}–{fm['away']}: {e}")

    pairs = []
    lacking = 0
    for f in sorted((out / "fotmob").glob("*.json")) if (out / "fotmob").exists() else []:
        fmd = _read(f)
        if fmd and fmd.get("season") == SEASON and fmd.get("oldb_id") in by_id:
            pairs.append((by_id[fmd["oldb_id"]], fmd))
            if not CORE_STATS <= set(fmd.get("stats") or {}):
                lacking += 1
    if pairs:
        _write(out / "teamstats.json", {"updated_at": at, **build_teamstats(aggregate(pairs))})
    note = f"{len(pairs)} Spiele ausgewertet" + (f", {unmatched} Spiel ohne Zuordnung" if unmatched == 1 else f", {unmatched} Spiele ohne Zuordnung" if unmatched else "")
    if lacking:
        note += f", {lacking} ohne Kernwerte (xG, Pässe oder Schüsse fehlen – Format geändert?)"
    status["fotmob"] = {"ok": not errors, "at": at, "error": "; ".join(errors) or None, "note": note}


def _update_players(out: Path, get: Callable[[str], str], now: datetime, at: str, status: dict) -> None:
    """Spieler aus den FotMob-Spieldateien sammeln, fällige Profile laden, Index schreiben."""
    seen: dict[int, dict] = {}
    files = sorted((out / "fotmob").glob("*.json")) if (out / "fotmob").exists() else []
    for f in files:
        m = _read(f) or {}
        if m.get("season") != SEASON:
            continue
        for p in m.get("players") or []:
            if not p.get("id") or not p.get("minutes"):
                continue
            e = seen.setdefault(p["id"], {"id": p["id"], "name": p.get("name"), "team": p.get("team"), "minutes": 0, "apps": 0, "ratings": [], "md": -1})
            e["minutes"] += p["minutes"]
            e["apps"] += 1
            if p.get("rating") is not None:
                e["ratings"].append(p["rating"])
            if m.get("matchday", 0) >= e["md"]:
                e["md"], e["team"], e["name"] = m.get("matchday", 0), p.get("team"), p.get("name")

    def fetched(pid: int) -> datetime | None:
        prof = _read(out / "players" / f"{pid}.json")
        return datetime.fromisoformat(prof["fetched_at"]) if prof and prof.get("fetched_at") else None

    due = []
    for pid in seen:
        t = fetched(pid)
        if t is None or now - t > PLAYER_FRESH:
            due.append((t or datetime.min.replace(tzinfo=now.tzinfo), pid))
    errors = []
    for _, pid in sorted(due)[:PLAYER_CAP]:
        try:
            nd = next_data(get(player_url(pid)))
            if nd is None:
                raise RuntimeError("Keine eingebetteten Daten")
            _write(out / "players" / f"{pid}.json", {**parse_player(nd), "fetched_at": at})
        except Exception as e:
            errors.append(f"{pid}: {e}")

    index, fresh = [], 0
    for pid, e in seen.items():
        prof = _read(out / "players" / f"{pid}.json") or {}
        if prof.get("fetched_at") and now - datetime.fromisoformat(prof["fetched_at"]) <= PLAYER_FRESH:
            fresh += 1
        main = next((p for p in prof.get("positions") or [] if p.get("main")), None)
        team = prof["team"] if prof else e["team"]  # Profil kennt den aktuellen Verein (auch außerhalb der Liga)
        index.append({"id": pid, "name": e["name"], "team": team, "team_name": prof.get("team_name"), "pos": main["short"] if main else None,
                      "age": prof.get("age"), "minutes": e["minutes"], "apps": e["apps"],
                      "rating": round(sum(e["ratings"]) / len(e["ratings"]), 2) if e["ratings"] else None})
    if index:
        index.sort(key=lambda x: (x["team"] or "", -x["minutes"]))
        _write(out / "players.json", {"updated_at": at, "players": index})
    status["fotmob_players"] = {"ok": len(errors) < max(1, len(due[:PLAYER_CAP])) or not due, "at": at,
                                "error": "; ".join(errors[:5]) + (f" (+{len(errors) - 5})" if len(errors) > 5 else "") or None,
                                "note": f"{fresh} von {len(seen)} Profilen aktuell"}


def run_update(out: Path, fetch: Fetcher, now: datetime, sleep: Callable[[float], None] = time.sleep) -> dict:
    out = Path(out)
    at = now.isoformat(timespec="seconds")
    status: dict[str, dict] = {}
    first_request = [True]

    def get(url: str) -> str:
        if not first_request[0]:
            sleep(PAUSE_S)
        first_request[0] = False
        try:
            r = fetch(url)
        except Exception:  # einmal nachfassen, z. B. nach einer Zeitüberschreitung
            sleep(PAUSE_S * 3)
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

    _update_fotmob(out, get, matchdays, now, at, status)
    _update_players(out, get, now, at, status)

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
    try:
        run_forecast(out, get, matchdays, current, teams_out, now, at, status)
    except Exception as e:  # Prognose darf den übrigen Lauf nicht kippen
        status["prognose"] = {"ok": False, "at": at, "error": f"{type(e).__name__}: {e}"}
    _write(out / "status" / "sources.json", status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aktualisiert Spielplan, Tabelle und Aufstellungen.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    status = run_update(args.out, lambda u: probe.http_fetch(u), datetime.now(timezone.utc), sleep=lambda s: time.sleep(s))
    for k, v in status.items():
        print(f"{'OK  ' if v['ok'] else 'FAIL'} {k:22} {v.get('note') or ''} {v['error'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

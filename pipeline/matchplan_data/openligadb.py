"""OpenLigaDB: Spielplan, Ergebnisse, Torschützen, Tabelle."""

from __future__ import annotations

from .teams import team_by_oldb

BASE = "https://api.openligadb.de"


def matchday_url(season: int, md: int) -> str:
    return f"{BASE}/getmatchdata/bl1/{season}/{md}"


def table_url(season: int) -> str:
    return f"{BASE}/getbltable/bl1/{season}"


def _result(raw: dict, type_id: int) -> list[int] | None:
    for r in raw.get("matchResults") or []:
        if r.get("resultTypeID") == type_id:
            return [r["pointsTeam1"], r["pointsTeam2"]]
    return None


def transform_matches(raw: list[dict]) -> list[dict]:
    out = []
    for m in raw:
        finished = bool(m.get("matchIsFinished"))
        out.append({
            "id": m["matchID"],
            "kickoff": m.get("matchDateTimeUTC") or None,
            "home": team_by_oldb(m["team1"]["teamId"]).key,
            "away": team_by_oldb(m["team2"]["teamId"]).key,
            "finished": finished,
            "score": _result(m, 2) if finished else None,
            "halftime": _result(m, 1) if finished else None,
            "goals": [
                {
                    "minute": g.get("matchMinute"),
                    "team": team_by_oldb(g["scoringTeamId"]).key,
                    "scorer": g.get("goalGetterName") or "",
                    "penalty": bool(g.get("isPenalty")),
                    "own_goal": bool(g.get("isOwnGoal")),
                }
                for g in (m.get("goals") or [])
            ],
        })
    return out


def current_matchday(matchdays: dict[int, list[dict]]) -> int:
    for md in sorted(matchdays):
        if any(not m["finished"] for m in matchdays[md]):
            return md
    return 34


def _letter(match: dict, key: str) -> str:
    h, a = match["score"]
    mine, theirs = (h, a) if match["home"] == key else (a, h)
    return "S" if mine > theirs else "U" if mine == theirs else "N"


def transform_table(raw: list[dict], matches: list[dict]) -> list[dict]:
    done = sorted((m for m in matches if m["finished"] and m["score"]), key=lambda m: m["kickoff"] or "")
    rows = []
    for rank, r in enumerate(raw, start=1):
        key = team_by_oldb(r["teamInfoId"]).key
        mine = [m for m in done if key in (m["home"], m["away"])][-5:]
        rows.append({
            "rank": rank, "team": key, "played": r["matches"], "won": r["won"], "draw": r["draw"], "lost": r["lost"],
            "goals": r["goals"], "against": r["opponentGoals"], "diff": r["goalDiff"], "points": r["points"],
            "form": [_letter(m, key) for m in mine],
        })
    return rows

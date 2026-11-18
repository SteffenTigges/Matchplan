"""FotMob: Spielplan mit FotMob-Kennungen und Spielstatistik aus den in die Seiten eingebetteten Daten."""

from __future__ import annotations

import json
import re

from .teams import team_by_fotmob

BASE = "https://www.fotmob.com"
LEAGUE_URL = f"{BASE}/leagues/54/fixtures/bundesliga"

_NEXT = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_COUNT_PCT = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*\((\d+(?:\.\d+)?)%\)\s*$")

TEAM_STATS = {
    "BallPossesion", "expected_goals", "expected_goals_open_play", "expected_goals_set_play", "expected_goals_on_target",
    "total_shots", "ShotsOnTarget", "shots_inside_box", "blocked_shots", "big_chance", "big_chance_missed_title",
    "passes", "accurate_passes", "own_half_passes", "opposition_half_passes", "long_balls_accurate", "accurate_crosses",
    "touches_opp_box", "corners", "Offsides", "matchstats.headers.tackles", "interceptions", "shot_blocks", "clearances",
    "keeper_saves", "duel_won", "ground_duels_won", "aerials_won", "dribbles_succeeded", "fouls", "yellow_cards", "red_cards",
}
RENAME = {"matchstats.headers.tackles": "tackles"}

PLAYER_STATS = {
    "minutes_played": "minutes", "rating_title": "rating", "goals": "goals", "assists": "assists", "expected_goals": "xg",
    "expected_assists": "xa", "total_shots": "shots", "chances_created": "key_passes", "touches_opp_box": "touches_box",
    "matchstats.headers.tackles": "tackles", "interceptions": "interceptions", "recoveries": "recoveries",
    "duel_won": "duels_won", "duel_lost": "duels_lost", "passes_into_final_third": "final_third_passes",
    "dribbles_succeeded": "dribbles", "touches": "touches",
}


def next_data(html: str) -> dict | None:
    m = _NEXT.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def to_number(v):
    """'366 (80%)' → {'n': 366, 'pct': 80}; '2.23' → 2.23; Zahlen bleiben; sonst None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    m = _COUNT_PCT.match(s)
    if m:
        n, pct = float(m.group(1)), float(m.group(2))
        return {"n": int(n) if n.is_integer() else n, "pct": int(pct) if pct.is_integer() else pct}
    try:
        f = float(s)
    except ValueError:
        return None
    return int(f) if f.is_integer() and "." not in s else f


def parse_league(data: dict) -> list[dict]:
    out = []
    for m in data["props"]["pageProps"]["fixtures"]["allMatches"]:
        st = m.get("status") or {}
        out.append({
            "fm_id": int(m["id"]),
            "url": BASE + m["pageUrl"].split("#")[0],
            "round": int(m["round"]),
            "home": team_by_fotmob(m["home"]["id"]).key,
            "away": team_by_fotmob(m["away"]["id"]).key,
            "finished": bool(st.get("finished")) and not st.get("cancelled"),
            "kickoff": st.get("utcTime"),
        })
    return out


def _result(s: dict) -> str:
    t = s.get("eventType")
    if t == "Goal":
        return "goal"
    if t == "Post":
        return "post"
    if s.get("isBlocked"):
        return "blocked"
    return "saved" if t == "AttemptSaved" else "miss"


def _key(team_id) -> str | None:
    try:
        return team_by_fotmob(team_id).key
    except (KeyError, ValueError, TypeError):
        return None


def parse_match(data: dict) -> dict:
    pp = data["props"]["pageProps"]
    c = pp.get("content") or {}

    stats: dict[str, list] = {}
    try:
        groups = c["stats"]["Periods"]["All"]["stats"]
    except (KeyError, TypeError):
        groups = []
    for g in groups:
        for s in g.get("stats") or []:
            k = s.get("key")
            vals = s.get("stats") or [None, None]
            if k in TEAM_STATS and vals != [None, None]:
                stats[RENAME.get(k, k)] = [to_number(vals[0]), to_number(vals[1])]

    shots = [
        {
            "team": _key(s.get("teamId")), "player": s.get("playerName"), "min": s.get("min"),
            "x": s.get("x"), "y": s.get("y"), "xg": s.get("expectedGoals"), "xgot": s.get("expectedGoalsOnTarget"),
            "situation": s.get("situation"), "type": s.get("shotType"), "result": _result(s), "own_goal": bool(s.get("isOwnGoal")),
        }
        for s in ((c.get("shotmap") or {}).get("shots") or [])
    ]

    mom = ((c.get("momentum") or {}).get("main") or {}).get("data")
    momentum = [[p["minute"], p["value"]] for p in mom] if mom else None

    az = c.get("attackingZones")
    zones = {side: az[side]["total"] for side in ("home", "away")} if az and az.get("home") and az.get("away") else None

    lineups = None
    lu = c.get("lineup") or {}
    if lu.get("homeTeam") and lu.get("awayTeam"):
        def team(t: dict) -> dict:
            return {
                "team": _key(t.get("id")), "formation": t.get("formation"), "rating": t.get("rating"),
                "players": [
                    {"name": p.get("name"), "pos_id": p.get("positionId"), "rating": (p.get("performance") or {}).get("rating"),
                     "captain": bool(p.get("isCaptain")), "x": (p.get("verticalLayout") or {}).get("x"), "y": (p.get("verticalLayout") or {}).get("y")}
                    for p in t.get("starters") or []
                ],
            }
        lineups = {"home": team(lu["homeTeam"]), "away": team(lu["awayTeam"])}

    players = []
    for p in (c.get("playerStats") or {}).values():
        row = {"team": _key(p.get("teamId")), "name": p.get("name"), "keeper": bool(p.get("isGoalkeeper"))}
        for g in p.get("stats") or []:
            for s in (g.get("stats") or {}).values():
                field = PLAYER_STATS.get(s.get("key"))
                if field and field not in row:
                    row[field] = to_number((s.get("stat") or {}).get("value"))
        players.append(row)

    return {"fm_id": int(pp.get("general", {}).get("matchId") or 0), "stats": stats, "shots": shots,
            "momentum": momentum, "zones": zones, "lineups": lineups, "players": players}

"""FotMob: Spielplan mit FotMob-Kennungen und Spielstatistik aus den in die Seiten eingebetteten Daten."""

from __future__ import annotations

import json
import re

from .teams import team_by_fotmob

BASE = "https://www.fotmob.com"
LEAGUE_URL = f"{BASE}/leagues/54/fixtures/bundesliga"
FORMAT_VERSION = 2  # erhöhen, wenn gespeicherte Spieldateien neu geladen werden müssen

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


def _num(v) -> float | int | None:
    """Nur echte Zahlen durchlassen (auch aus Text wie '7.5')."""
    n = to_number(v)
    return n if isinstance(n, (int, float)) else None


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
            "team": _key(s.get("teamId")), "player": s.get("playerName"), "min": _num(s.get("min")),
            "x": _num(s.get("x")), "y": _num(s.get("y")), "xg": _num(s.get("expectedGoals")), "xgot": _num(s.get("expectedGoalsOnTarget")),
            "situation": s.get("situation"), "type": s.get("shotType"), "result": _result(s), "own_goal": bool(s.get("isOwnGoal")),
        }
        for s in ((c.get("shotmap") or {}).get("shots") or [])
    ]

    mom = ((c.get("momentum") or {}).get("main") or {}).get("data")
    momentum = [[p["minute"], p["value"]] for p in mom] if mom else None

    az = c.get("attackingZones")
    zones = None
    if az and az.get("home") and az.get("away"):
        zz = {side: {k: _num((az[side].get("total") or {}).get(k)) for k in ("left", "center", "right")} for side in ("home", "away")}
        zones = zz if all(v is not None for z in zz.values() for v in z.values()) else None

    lineups = None
    lu = c.get("lineup") or {}
    if lu.get("homeTeam") and lu.get("awayTeam"):
        def team(t: dict) -> dict:
            return {
                "team": _key(t.get("id")), "formation": t.get("formation"), "rating": _num(t.get("rating")),
                "players": [
                    {"id": _num(p.get("id")), "name": p.get("name"), "pos_id": _num(p.get("positionId")), "rating": _num((p.get("performance") or {}).get("rating")),
                     "captain": bool(p.get("isCaptain")), "x": (p.get("verticalLayout") or {}).get("x"), "y": (p.get("verticalLayout") or {}).get("y")}
                    for p in t.get("starters") or []
                ],
            }
        lineups = {"home": team(lu["homeTeam"]), "away": team(lu["awayTeam"])}

    players = []
    for pid, p in (c.get("playerStats") or {}).items():
        row = {"id": _num(p.get("id")) or _num(pid), "team": _key(p.get("teamId")), "name": p.get("name"), "keeper": bool(p.get("isGoalkeeper"))}
        for g in p.get("stats") or []:
            for s in (g.get("stats") or {}).values():
                field = PLAYER_STATS.get(s.get("key"))
                if field and field not in row:
                    row[field] = _num((s.get("stat") or {}).get("value"))
        players.append(row)

    return {"v": FORMAT_VERSION, "fm_id": int(pp.get("general", {}).get("matchId") or 0), "stats": stats, "shots": shots,
            "momentum": momentum, "zones": zones, "lineups": lineups, "players": players}


# ---------------- Spielerseiten ----------------

def player_url(player_id: int) -> str:
    return f"{BASE}/players/{player_id}/x"


GROUP_DE = {"Shooting": "Abschluss", "Passing": "Passspiel", "Possession": "Ballbesitz & Dribbling",
            "Defending": "Defensive", "Discipline": "Disziplin", "Goalkeeping": "Torwartspiel"}
POS_DE = {"Goalkeeper": "Torwart", "Center Back": "Innenverteidiger", "Left Back": "Linksverteidiger",
          "Right Back": "Rechtsverteidiger", "Left Wing-Back": "Linker Schienenspieler", "Right Wing-Back": "Rechter Schienenspieler",
          "Defensive Midfielder": "Defensives Mittelfeld", "Central Midfielder": "Zentrales Mittelfeld",
          "Attacking Midfielder": "Offensives Mittelfeld", "Left Midfielder": "Linkes Mittelfeld", "Right Midfielder": "Rechtes Mittelfeld",
          "Left Winger": "Linksaußen", "Right Winger": "Rechtsaußen", "Striker": "Stürmer"}
FOOT_DE = {"both": "beidfüßig", "right": "rechts", "left": "links"}
STAT_DE = {
    "goals": "Tore", "expected_goals": "xG", "expected_goals_on_target": "xGOT", "non_penalty_xg": "xG ohne Elfmeter",
    "shots": "Schüsse", "ShotsOnTarget": "Schüsse aufs Tor", "assists": "Vorlagen", "expected_assists": "xA",
    "successful_passes": "Angekommene Pässe", "successful_passes_accuracy": "Passquote", "long_balls_accurate": "Lange Bälle angekommen",
    "long_ball_succeeeded_accuracy": "Quote lange Bälle", "chances_created": "Torchancen vorbereitet", "crosses_succeeeded": "Flanken angekommen",
    "crosses_succeeeded_accuracy": "Flankenquote", "dribbles_succeeded": "Erfolgreiche Dribblings", "won_contest_subtitle": "Dribbling-Quote",
    "touches": "Ballkontakte", "touches_opp_box": "Ballaktionen im gegn. Strafraum", "dispossessed": "Ballverluste im Zweikampf",
    "duel_won": "Zweikämpfe gewonnen", "duel_won_percent": "Zweikampfquote", "aerials_won": "Luftzweikämpfe gewonnen",
    "aerials_won_percent": "Luftzweikampfquote", "fouls_won": "Gefoult worden", "matchstats.headers.tackles": "Tacklings",
    "tackles_succeeded": "Tacklings", "interceptions": "Abgefangene Bälle", "shot_blocked": "Geblockte Schüsse", "clearances": "Klärungen",
    "recoveries": "Ballgewinne", "poss_won_att_3rd_team_title": "Ballgewinne im Angriffsdrittel", "dribbled_past": "Ausgedribbelt worden",
    "fouls": "Fouls", "yellow_cards": "Gelbe Karten", "red_cards": "Rote Karten", "saves": "Paraden", "save_percentage": "Paradenquote",
    "goals_conceded": "Gegentore", "clean_sheet_team_title": "Spiele ohne Gegentor", "goals_prevented": "Verhinderte Tore",
    "headed_shots": "Kopfballschüsse", "line_breaking_passes": "Linien brechende Pässe", "big_chance_created_team_title": "Großchancen vorbereitet",
    "penalty_won_title": "Elfmeter herausgeholt", "defensive_actions": "Defensivaktionen", "blocked_shots": "Geblockte Abschlüsse",
    "goals_conceded_while_on_pitch": "Gegentore während auf dem Platz", "expected_goals_against_while_on_pitch": "Zugelassene xG während auf dem Platz",
}


def _date(v) -> str | None:
    if isinstance(v, dict):
        v = v.get("utcTime") or v.get("dateValue")
    return str(v)[:10] if v else None


def _info(data: dict, title: str):
    for i in data.get("playerInformation") or []:
        if i.get("title") == title:
            return i.get("value") or {}
    return {}


def _career(entries: list[dict]) -> list[dict]:
    out = []
    for e in entries or []:
        tt = (e.get("transferType") or {}).get("localizationKey") or ""
        kind = "Leihe" if tt == "on_loan" else "Leihende" if "back_from_loan" in tt else None
        out.append({"team": e.get("team"), "start": _date(e.get("startDate")), "end": _date(e.get("endDate")),
                    "apps": _num(e.get("appearances")), "goals": _num(e.get("goals")), "kind": kind})
    return out


def parse_player(data: dict) -> dict:
    d = data["props"]["pageProps"]["data"]
    pt = d.get("primaryTeam") or {}
    team = _key(pt.get("teamId"))
    foot = _info(d, "Preferred foot").get("key")
    positions = sorted(
        ({"label": POS_DE.get((p.get("strPos") or {}).get("label"), (p.get("strPos") or {}).get("label")),
          "short": (p.get("strPosShort") or {}).get("label"), "main": bool(p.get("isMainPosition"))}
         for p in (d.get("positionDescription") or {}).get("positions") or []),
        key=lambda p: not p["main"],
    )
    stats = []
    for g in ((d.get("firstSeasonStats") or {}).get("statsSection") or {}).get("items") or []:
        for s in g.get("items") or []:
            key = s.get("localizedTitleId")
            stats.append({"group": GROUP_DE.get(g.get("title"), g.get("title")), "key": key,
                          "title": STAT_DE.get(key, s.get("title")), "value": _num(s.get("statValue")),
                          "per90": _num(s.get("per90")), "pct": _num(s.get("percentileRankPer90"))})
    tr = d.get("traits")
    traits = {"title": tr.get("title"), "items": [{"key": i.get("key"), "title": i.get("title"), "value": _num(i.get("value"))} for i in tr.get("items") or []]} if tr else None
    ci = (d.get("careerHistory") or {}).get("careerItems") or {}
    fee_de = {"on loan": "Leihe", "free transfer": "ablösefrei", "back from loan": "Leihende"}
    return {
        "id": _num(d.get("id")), "name": d.get("name"), "team": team, "team_name": pt.get("teamName"),
        "birth_date": _date(d.get("birthDate")), "age": _num(_info(d, "Age").get("numberValue")),
        "height_cm": _num(_info(d, "Height").get("numberValue")), "foot": FOOT_DE.get(foot, foot),
        "country": _info(d, "Country").get("fallback"), "shirt": _num(_info(d, "Shirt").get("numberValue")),
        "market_value": _num(_info(d, "Market value").get("numberValue")), "contract_end": _date(d.get("contractEnd")),
        "positions": positions, "stats": stats, "traits": traits,
        "career": {"senior": _career((ci.get("senior") or {}).get("teamEntries")),
                   "youth": _career((ci.get("youth") or {}).get("teamEntries")),
                   "national": _career((ci.get("national team") or {}).get("teamEntries")),
                   "national_youth": _career((ci.get("national team youth") or {}).get("teamEntries"))},
        "transfers": [{"from": t.get("fromClub"), "to": t.get("toClub"), "date": _date(t.get("transferDate")),
                       "fee": fee_de.get(((t.get("fee") or {}).get("feeText") or "").lower(), (t.get("fee") or {}).get("feeText")),
                       "loan": bool(t.get("onLoan"))} for t in d.get("transfers") or []],
    }

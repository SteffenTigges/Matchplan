import copy
import json
from pathlib import Path

from matchplan_data.fotmob import next_data, parse_league, parse_match, to_number

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_next_data_extracts_json():
    html = '<html><script id="__NEXT_DATA__" type="application/json">{"props": {"a": 1}}</script></html>'
    assert next_data(html) == {"props": {"a": 1}}
    assert next_data("<html>nichts</html>") is None


def test_parse_league_maps_teams_and_rounds():
    ms = parse_league(load("fotmob_league.json"))
    assert ms[0] == {"fm_id": 5881219, "url": "https://www.fotmob.com/match/5881219",
                     "round": 9, "home": "TSG", "away": "S04", "finished": True, "kickoff": "2026-11-08T18:30:00Z"}
    assert ms[2]["home"] == "FCB" and ms[2]["finished"] is False


def test_parses_count_and_percent():
    assert to_number("366 (80%)") == {"n": 366, "pct": 80}
    assert to_number("2.23") == 2.23
    assert to_number(49) == 49
    assert to_number(None) is None


def test_parses_team_stats():
    st = parse_match(load("fotmob_match.json"))["stats"]
    assert st["expected_goals"] == [2.23, 2.6]
    assert st["BallPossesion"] == [49, 51]
    assert st["accurate_passes"] == [{"n": 366, "pct": 80}, {"n": 346, "pct": 74}]
    assert st["tackles"] == [15, 14]


def test_parses_shots_with_xg_and_result():
    shots = parse_match(load("fotmob_match.json"))["shots"]
    assert len(shots) == 6
    goal = shots[0]
    assert goal["team"] == "TSG" and goal["player"] == "Fisnik Asllani" and goal["result"] == "goal"
    assert round(goal["xg"], 3) == 0.362 and 0 <= goal["x"] <= 106 and 0 <= goal["y"] <= 69
    assert {s["result"] for s in shots} <= {"goal", "saved", "miss", "blocked", "post"}
    assert shots[4]["team"] == "S04"


def test_parses_lineups_with_formation_and_ratings():
    lu = parse_match(load("fotmob_match.json"))["lineups"]
    assert lu["home"]["formation"] == "4-2-3-1" and lu["home"]["rating"] == 7.4
    keeper = lu["home"]["players"][0]
    assert keeper["name"] == "Oliver Baumann" and keeper["rating"] == 7.5 and keeper["pos_id"] == 11


def test_parses_momentum_zones_and_players():
    m = parse_match(load("fotmob_match.json"))
    assert m["momentum"][:2] == [[0, 0], [1, -11]]
    assert m["zones"]["home"] == {"left": 28, "center": 24, "right": 48}
    p = m["players"][0]
    assert p["minutes"] == 14 and p["rating"] == 5.97 and p["xg"] == 0.05 and p["team"] in ("TSG", "S04")


def test_missing_sections_are_none():
    data = load("fotmob_match.json")
    c = data["props"]["pageProps"]["content"]
    for k in ("shotmap", "momentum", "attackingZones", "lineup", "playerStats"):
        c.pop(k)
    m = parse_match(data)
    assert m["shots"] == [] and m["momentum"] is None and m["zones"] is None and m["lineups"] is None and m["players"] == []
    assert m["stats"]["expected_goals"] == [2.23, 2.6]


def test_numbers_from_fotmob_are_coerced():
    data = load("fotmob_match.json")
    c = data["props"]["pageProps"]["content"]
    c["lineup"]["homeTeam"]["starters"][0]["performance"]["rating"] = "7.5"
    c["shotmap"]["shots"][0]["min"] = "10"
    m = parse_match(data)
    assert m["lineups"]["home"]["players"][0]["rating"] == 7.5 and m["shots"][0]["min"] == 10


def test_incomplete_zones_are_dropped():
    data = load("fotmob_match.json")
    del data["props"]["pageProps"]["content"]["attackingZones"]["home"]["total"]["center"]
    assert parse_match(data)["zones"] is None


def test_match_has_player_ids():
    m = parse_match(load("fotmob_match.json"))
    assert m["v"] == 5
    assert m["lineups"]["home"]["players"][0]["id"] == 178778
    assert all(isinstance(p["id"], int) for p in m["players"])


def test_player_season_rows_when_present():
    from matchplan_data.fotmob import _seasons
    rows = _seasons([{"seasonName": "2024/2025", "appearances": "30", "goals": "9", "assists": "4", "rating": {"rating": "7.12"},
                      "tournamentStats": [{"isFriendly": False, "leagueId": 54, "leagueName": "Bundesliga", "appearances": "28", "goals": "8", "assists": "4", "rating": {"rating": "7.1"}},
                                          {"isFriendly": True, "leagueName": "Club Friendlies", "appearances": "3"}]}])
    assert rows == [{"season": "2024/2025", "apps": 30, "goals": 9, "assists": 4, "rating": 7.12,
                     "competitions": [{"league": "Bundesliga", "league_id": 54, "apps": 28, "goals": 8, "assists": 4, "rating": 7.1}]}]


def test_referee_from_info_box():
    from matchplan_data.fotmob import referee
    nd = {"props": {"pageProps": {"content": {"matchFacts": {"infoBox": {"Referee": {"text": "Martin Petersen", "id": 1001075723, "country": "Germany"}}}}}}}
    assert referee(nd) == {"name": "Martin Petersen", "id": 1001075723, "country": "Germany"}
    assert referee({"props": {"pageProps": {"content": {"matchFacts": {"infoBox": {"Referee": None}}}}}}) is None
    assert referee({}) is None


def _ev_page(events, status=None):
    return {"props": {"pageProps": {"header": {"teams": [{"score": 1}, {"score": 2}], "status": status or {}},
                                    "content": {"matchFacts": {"events": {"events": events}}}}}}


def test_parse_events_goal_card_sub():
    from matchplan_data.fotmob import parse_events
    evs = parse_events(_ev_page([
        {"type": "Goal", "time": 12, "overloadTime": None, "isHome": False, "player": {"id": 1407250, "name": "Mikey Moore"},
         "assistStr": "assist by Saïd El Mala", "newScore": [0, 1], "ownGoal": None, "shotmapEvent": {"situation": "RegularPlay"}},
        {"type": "Substitution", "time": 20, "overloadTime": 0, "isHome": True, "swap": [{"name": "Tom Bischof", "id": "1286183"}, {"name": "Harry Kane", "id": "194165"}]},
        {"type": "Card", "time": 56, "isHome": False, "player": {"id": 1527363, "name": "Paul Okon-Engstler"}, "card": "Yellow"},
        {"type": "Card", "time": 88, "isHome": True, "player": {"id": 1, "name": "X"}, "card": "YellowRed"},
        {"type": "Half", "time": 45, "halfStrShort": "HT"},
        {"type": "Goal", "time": 90, "overloadTime": 3, "isHome": True, "player": {"id": 2, "name": "Y"}, "newScore": [1, 1], "shotmapEvent": {"situation": "Penalty"}}]))
    assert evs[0] == {"min": 12, "plus": None, "home": False, "type": "goal", "player": "Mikey Moore", "player_id": 1407250,
                      "assist": "Saïd El Mala", "score": [0, 1], "own_goal": False, "penalty": False}
    assert evs[1]["in"] == "Tom Bischof" and evs[1]["out_id"] == 194165
    assert evs[2]["card"] == "yellow" and evs[3]["card"] == "yellowred" and evs[4]["text"] == "HT"
    assert evs[5]["plus"] == 3 and evs[5]["penalty"] is True


def test_parse_status_live():
    from matchplan_data.fotmob import parse_status
    st = parse_status(_ev_page([], {"started": True, "finished": False, "liveTime": {"short": "57'"}, "reason": {}}))
    assert st == {"started": True, "finished": False, "cancelled": False, "minute": "57'", "reason": None, "score": [1, 2]}


def test_live_minute_is_cleaned():
    from matchplan_data.fotmob import parse_status
    st = parse_status(_ev_page([], {"started": True, "liveTime": {"short": "25‎’‎"}}))
    assert st["minute"] == "25'"

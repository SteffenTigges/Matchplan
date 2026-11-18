import json
from pathlib import Path

from matchplan_data.openligadb import current_matchday, transform_matches, transform_table
from matchplan_data.teams import TEAMS

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_finished_match_has_score_and_goals():
    m = transform_matches(load("openligadb_md9.json"))[0]
    assert m["home"] == "BVB" and m["away"] == "SVE" and m["score"] == [2, 1] and m["halftime"] == [0, 0]
    assert m["kickoff"] == "2026-11-07T14:30:00Z" and m["id"] == 83228 and m["finished"] is True
    assert m["goals"][2] == {"minute": 81, "team": "SVE", "scorer": "N. Futkeu", "penalty": False, "own_goal": False}


def test_penalty_and_own_goal_flags():
    ms = transform_matches(load("openligadb_md9.json"))
    assert ms[1]["goals"][2]["penalty"] is True
    assert ms[2]["goals"][0] == {"minute": 55, "team": "SCF", "scorer": "R. Khedira", "penalty": False, "own_goal": True}


def test_unfinished_match_has_no_score():
    m = transform_matches(load("openligadb_md10.json"))[0]
    assert m["finished"] is False and m["score"] is None and m["halftime"] is None


from datetime import datetime, timezone

NOW = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)


def test_current_matchday_is_first_with_unfinished_match():
    mds = {9: transform_matches(load("openligadb_md9.json")), 10: transform_matches(load("openligadb_md10.json"))}
    assert current_matchday(mds, NOW) == 10


def test_postponed_match_does_not_freeze_current_matchday():
    md8 = [{"id": 1, "kickoff": "2027-02-10T19:30:00Z", "home": "FCU", "away": "SGE", "finished": False}]
    md9 = transform_matches(load("openligadb_md9.json"))
    md10 = transform_matches(load("openligadb_md10.json"))
    assert current_matchday({8: md8, 9: md9, 10: md10}, NOW) == 10


def test_running_match_keeps_its_matchday():
    md10 = transform_matches(load("openligadb_md10.json"))
    during = datetime(2026, 11, 20, 20, 15, tzinfo=timezone.utc)  # Bayern–Köln läuft seit 45 Minuten
    md11 = [{"id": 9, "kickoff": "2026-11-27T19:30:00Z", "home": "FCB", "away": "BVB", "finished": False}]
    assert current_matchday({10: md10, 11: md11}, during) == 10


def test_current_matchday_after_season_is_34():
    assert current_matchday({34: transform_matches(load("openligadb_md9.json"))}, NOW) == 34


def test_no_known_matches_keeps_previous_or_none():
    assert current_matchday({1: [], 2: []}, NOW, previous=10) == 10
    assert current_matchday({1: [], 2: []}, NOW) is None


def test_table_rows_have_keys_and_form():
    rows = transform_table(load("openligadb_table.json"), transform_matches(load("openligadb_md9.json")))
    assert rows[0]["team"] == "FCB" and rows[0]["points"] == 21 and rows[0]["rank"] == 1
    assert rows[0]["against"] == 9 and rows[0]["diff"] == 20 and rows[0]["played"] == 9
    assert rows[1]["team"] == "BVB" and rows[1]["form"] == ["S"]
    assert rows[2]["form"] == ["S"]


def test_registry_has_18_unique_teams():
    assert len(TEAMS) == 18 and len({t.oldb_id for t in TEAMS}) == 18 and len({t.key for t in TEAMS}) == 18

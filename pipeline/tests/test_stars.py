import json

import pytest

from matchplan_data.similar import group_of
from matchplan_data.stars import age_in_season, now_values, same_age, then_values, top_rated


def test_age_in_season():
    assert age_in_season("2000-07-21", "2021/2022") == 21
    assert age_in_season("2000-10-01", "2021/2022") == 20
    assert age_in_season(None, "2021/2022") is None


def test_top_rated_needs_minutes():
    text = json.dumps({"TopLists": [{"StatList": [
        {"ParticipantName": "A", "ParticiantId": 1, "StatValue": 8.1, "MinutesPlayed": 300, "TeamName": "X"},
        {"ParticipantName": "B", "ParticiantId": 2, "StatValue": 7.9, "MinutesPlayed": 900, "TeamName": "Y"},
        {"ParticipantName": "C", "ParticiantId": 3, "StatValue": 7.5, "MinutesPlayed": 880, "TeamName": "Z"}]}]})
    assert [r["id"] for r in top_rated(text)] == [2, 3]


def season(name, apps, goals, assists, rating, league_id=54, league="Bundesliga"):
    return {"season": name, "apps": apps, "goals": goals, "assists": assists, "rating": rating,
            "competitions": [{"league": league, "league_id": league_id, "apps": apps, "goals": goals, "assists": assists, "rating": rating}]}


YOUNG = {"id": 1, "name": "Jung", "birth_date": "2005-03-01", "positions": [{"short": "ST", "main": True}],
         "seasons": [season("2026/2027", 9, 5, 2, 7.4)]}
STAR = {"id": 2, "name": "Haaland", "birth_date": "2000-07-21", "positions": [{"short": "ST", "main": True}], "star_rating": 7.9,
        "seasons": [season("2021/2022", 24, 22, 7, 7.6, 54, "Bundesliga"), season("2020/2021", 28, 27, 6, 7.8), season("2026/2027", 10, 9, 1, 7.9, 47, "Premier League")]}


def test_then_and_now_values():
    assert then_values(STAR, 21)["season"] == "2021/2022"
    assert now_values(YOUNG, "2026/2027")["ga"] == pytest.approx(7 / 9)


def test_same_age_comparison():
    out = same_age(YOUNG, [YOUNG, STAR], "2026/2027", group_of)
    assert out and out[0]["id"] == 2 and out[0]["then"]["age"] == 21 and out[0]["then"]["season"] == "2021/2022"
    assert 70 <= out[0]["score"] <= 100


def test_no_comparison_without_season_at_that_age():
    old_star = {**STAR, "seasons": [season("2026/2027", 10, 9, 1, 7.9)]}
    assert same_age(YOUNG, [old_star], "2026/2027", group_of) == []
    assert same_age({**YOUNG, "birth_date": "1995-01-01"}, [STAR], "2026/2027", group_of) == []

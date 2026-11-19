import pytest

from matchplan_data.referees import build_referees


def pair(home, away, score, ref, yellow=(2, 1), fouls=(10, 12), pens=0):
    m = {"home": home, "away": away, "score": score}
    fm = {"referee": {"name": ref, "id": 1}, "stats": {"yellow_cards": list(yellow), "red_cards": [0, 0], "fouls": list(fouls)},
          "shots": [{"situation": "Penalty"}] * pens}
    return m, fm


def test_referee_values_per_game():
    r = build_referees([pair("A", "B", [2, 0], "X", pens=1), pair("C", "A", [1, 1], "X", yellow=(4, 3)), pair("D", "E", [0, 1], "Y")], {})
    x = r["referees"]["X"]
    assert x["games"] == 2 and x["yellow_pg"] == 5.0 and x["penalties"] == 1 and x["fouls_pg"] == 22.0
    assert x["home_win"] == 0.5 and x["draw"] == 0.5 and x["teams"]["A"] == {"games": 2, "points": 4}
    assert r["league"]["yellow_pg"] == pytest.approx(13 / 3, abs=0.01)


def test_matches_without_referee_are_skipped():
    m, fm = pair("A", "B", [1, 0], "X")
    fm["referee"] = None
    assert build_referees([(m, fm)], {"5": {"name": "Z"}}) == {"league": {"yellow_pg": None, "fouls_pg": None, "penalties_pg": None}, "referees": {}, "upcoming": {"5": {"name": "Z"}}}

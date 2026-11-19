import pytest

from matchplan_data.similar import build_similar, could_be, group_of, style_similar

KEYS = ["goals", "expected_goals", "shots", "assists", "expected_assists", "chances_created", "touches_opp_box",
        "dribbles_succeeded", "successful_passes", "duel_won", "recoveries"]


def prof(pid, pos, pcts, age=27, per90=None, name=None):
    per90 = per90 or {}
    return {"id": pid, "name": name or f"P{pid}", "team": "FCB", "age": age,
            "positions": [{"short": pos, "main": True}],
            "stats": [{"key": k, "pct": p, "per90": per90.get(k)} for k, p in zip(KEYS, pcts)]}


def test_style_identical_is_100():
    a = prof(1, "ST", [90, 80, 70, 60, 20, 30, 85, 40, 10, 55, 35])
    b = prof(2, "ST", [90, 80, 70, 60, 20, 30, 85, 40, 10, 55, 35])
    c = prof(3, "ST", [10, 20, 30, 40, 80, 70, 15, 60, 90, 45, 65])
    out = style_similar(a, [a, b, c])
    assert out[0]["id"] == 2 and out[0]["score"] == pytest.approx(100)
    assert all(x["id"] != 1 for x in out) and out[-1]["id"] == 3


def test_needs_shared_keys():
    a = prof(1, "ST", [90] * 11)
    b = prof(2, "ST", [80] * 11)
    b["stats"] = b["stats"][:7]
    assert style_similar(a, [a, b]) == []


def test_same_group_only():
    a = prof(1, "ST", [90, 80, 70, 60, 20, 30, 85, 40, 10, 55, 35])
    b = prof(2, "CB", [90, 80, 70, 60, 20, 30, 85, 40, 10, 55, 35])
    assert style_similar(a, [a, b]) == []
    assert group_of(b) == "Abwehr" and group_of(a) == "Angriff" and group_of(prof(4, "GK", [1] * 11)) == "Tor"


IMP = {"expected_goals": 0.5, "expected_assists": 0.2, "chances_created": 1.5, "touches_opp_box": 6.0}


def test_could_be_only_young():
    young = prof(1, "ST", [50] * 11, age=21, per90={k: v * 0.9 for k, v in IMP.items()})
    old = prof(5, "ST", [50] * 11, age=26, per90=IMP)
    star = prof(2, "ST", [50] * 11, age=27, per90=IMP, name="Star")
    rows = {1: {"minutes": 900, "rating": 7.0}, 2: {"minutes": 1200, "rating": 7.8}, 5: {"minutes": 1200, "rating": 6.6}}
    out = could_be(young, [young, star, old], rows)
    assert out and out[0]["id"] == 2 and out[0]["score"] == pytest.approx(90, abs=0.5)
    assert could_be(old, [young, star, old], rows) == []


def test_missing_impact_value_skipped():
    young = prof(1, "ST", [50] * 11, age=20, per90=IMP)
    star = prof(2, "ST", [50] * 11, age=28, per90={**IMP, "chances_created": None})
    rows = {1: {"minutes": 900, "rating": 7.0}, 2: {"minutes": 1200, "rating": 7.9}}
    out = could_be(young, [young, star], rows)
    assert out[0]["score"] == pytest.approx(100) and out[0]["keys"] == 3


def test_build_similar_shape():
    a = prof(1, "ST", [90, 80, 70, 60, 20, 30, 85, 40, 10, 55, 35], age=20, per90=IMP)
    b = prof(2, "ST", [85, 75, 70, 60, 25, 30, 80, 45, 15, 50, 35], age=28, per90=IMP)
    res = build_similar([a, b], {1: {"minutes": 900, "rating": 7.0}, 2: {"minutes": 1500, "rating": 7.6}})
    assert set(res) == {1, 2} and res[1]["style"][0]["id"] == 2 and res[1]["could_be"][0]["id"] == 2

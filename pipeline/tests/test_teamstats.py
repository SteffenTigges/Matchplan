import pytest

from matchplan_data.teamstats import CATEGORIES, METRICS, aggregate, build_teamstats, rank, xpoints


def test_xpoints_certain_goal():
    h, a = xpoints([0.99, 0.99, 0.99], [])
    assert h == pytest.approx(3, abs=0.01) and a == pytest.approx(0, abs=0.01)


def test_xpoints_symmetric_split():
    h, a = xpoints([0.3, 0.2], [0.3, 0.2])
    assert h == pytest.approx(a) and 1.0 < h < 1.6


def stats(**kw):
    base = {"expected_goals": [1.0, 1.0], "total_shots": [10, 10], "BallPossesion": [50, 50], "touches_opp_box": [20, 20],
            "own_half_passes": [100, 100], "tackles": [10, 10], "interceptions": [5, 5], "fouls": [5, 5]}
    base.update(kw)
    return {"stats": base, "shots": []}


def match(home, away, score, mid):
    return {"id": mid, "home": home, "away": away, "finished": True, "score": score}


def test_averages_use_own_match_count():
    pairs = [
        (match("AAA", "BBB", [2, 0], 1), stats(expected_goals=[2.0, 0.5])),
        (match("AAA", "CCC", [1, 1], 2), stats(expected_goals=[1.0, 1.0])),
        (match("BBB", "CCC", [0, 0], 3), stats(expected_goals=[0.4, 0.6])),
    ]
    v = aggregate(pairs)
    assert v["AAA"]["matches"] == 2 and v["AAA"]["xg_pg"] == pytest.approx(1.5)
    assert v["BBB"]["matches"] == 2 and v["BBB"]["xg_pg"] == pytest.approx(0.45)
    assert v["AAA"]["points"] == 4 and v["AAA"]["clean_sheets"] == 1


def test_press_ratio_uses_measured_ball_wins():
    from matchplan_data.teamstats import add_pressing
    v = aggregate([(match("AAA", "BBB", [0, 0], 1), stats(own_half_passes=[100, 200], tackles=[10, 10], interceptions=[5, 5], fouls=[5, 5]))])
    add_pressing(v, {"AAA": {"won_att3_pg": 6.0, "won_mid_pg": 19.0}})
    assert v["AAA"]["won_att3_pg"] == 6.0 and v["AAA"]["press_ratio"] == pytest.approx(200 / 25)
    assert v["BBB"]["press_ratio"] is None and v["BBB"]["won_att3_pg"] is None


def test_parse_pressing():
    import json
    from matchplan_data.fotmob import parse_pressing
    text = json.dumps({"TopLists": [{"StatList": [{"TeamId": 9823, "StatValue": 6.3, "SubStatValue": 225.0, "MatchesPlayed": 9},
                                                  {"TeamId": 1, "StatValue": 1.0, "SubStatValue": 9.0, "MatchesPlayed": 9}]}]})
    assert parse_pressing(text) == {"FCB": {"won_att3_pg": 6.3, "won_mid_pg": 25.0}}


def test_ties_share_rank():
    assert rank({"A": 3, "B": 3, "C": 1}, higher_is_better=True) == {"A": 1, "B": 1, "C": 3}


def test_lower_is_better_ranks_smallest_first():
    assert rank({"A": 0.5, "B": 1.5, "C": 1.0}, higher_is_better=False) == {"A": 1, "C": 2, "B": 3}


def test_metrics_cover_all_categories():
    assert {m.category for m in METRICS} == set(CATEGORIES) and len(CATEGORIES) == 9
    assert len({m.key for m in METRICS}) == len(METRICS)


def test_build_teamstats_has_value_and_rank_per_metric():
    pairs = [(match("AAA", "BBB", [2, 0], 1), stats(expected_goals=[2.0, 0.5]))]
    ts = build_teamstats(aggregate(pairs))
    assert ts["teams"]["AAA"]["xg_pg"] == {"value": 2.0, "rank": 1}
    assert ts["teams"]["BBB"]["xg_pg"]["rank"] == 2
    assert ts["metrics"][0]["key"] == METRICS[0].key and "category" in ts["metrics"][0]


def test_missing_stats_do_not_lower_averages():
    pairs = [
        (match("AAA", "BBB", [1, 0], 1), stats(expected_goals=[2.0, 0.5])),
        (match("AAA", "BBB", [0, 0], 2), {"stats": {}, "shots": []}),
    ]
    v = aggregate(pairs)
    assert v["AAA"]["matches"] == 2 and v["AAA"]["points"] == 4
    assert v["AAA"]["xg_pg"] == pytest.approx(2.0) and v["AAA"]["possession"] == pytest.approx(0.5)


def test_metric_missing_for_everyone_is_unranked():
    pairs = [(match("AAA", "BBB", [1, 0], 1), {"stats": {"total_shots": [5, 3]}, "shots": []})]
    ts = build_teamstats(aggregate(pairs))
    assert ts["teams"]["AAA"]["xg_pg"] == {"value": None, "rank": None}
    assert ts["teams"]["AAA"]["won_att3_pg"] == {"value": None, "rank": None}
    assert ts["teams"]["AAA"]["shots_pg"] == {"value": 5.0, "rank": 1}

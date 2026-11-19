import math
import random

import pytest

from matchplan_data.predict import (Means, TeamGame, expected_goals, fit_calibration, markets, outcome_probs,
                                    score_matrix, strengths, tip)


def total(m):
    return sum(sum(r) for r in m)


def test_matrix_sums_to_one():
    for lh, la, rho in [(1.5, 1.1, -0.05), (0.2, 3.9, 0.05), (4.5, 0.3, -0.2)]:
        assert total(score_matrix(lh, la, rho)) == pytest.approx(1, abs=1e-9)


def test_dixon_coles_never_negative():
    for rho in [x / 100 for x in range(-20, 6)]:
        m = score_matrix(6.0, 0.1, rho)
        assert min(min(r) for r in m) >= 0


def test_dixon_coles_moves_low_scores():
    plain = score_matrix(1.4, 1.1, 0.0)
    dc = score_matrix(1.4, 1.1, -0.1)
    assert dc[0][0] > plain[0][0] and dc[1][1] > plain[1][1]


def test_tip_is_within_most_likely_outcome():
    m = score_matrix(1.9, 0.9, -0.05)
    h, d, a = outcome_probs(m)
    assert h > d and h > a
    th, ta = tip(m)
    assert th > ta


def test_tip_draw_when_draw_most_likely():
    m = [[0.0] * 11 for _ in range(11)]
    m[1][1], m[2][1], m[1][2], m[3][0] = 0.4, 0.2, 0.2, 0.2
    assert tip(m) == (1, 1)


def test_markets_from_matrix():
    m = score_matrix(1.5, 1.2, 0.0)
    mk = markets(m)
    p0h, p0a = math.exp(-1.5), math.exp(-1.2)
    assert mk["btts"] == pytest.approx((1 - p0h) * (1 - p0a), abs=1e-3)
    assert mk["home_clean_sheet"] == pytest.approx(p0a, abs=1e-3)
    lam = 2.7
    under = sum(math.exp(-lam) * lam**k / math.factorial(k) for k in range(3))
    assert mk["over25"] == pytest.approx(1 - under, abs=1e-3)


def g(md, team, opp, xf, xa, home=True):
    return TeamGame(md, team, opp, home, xf, xa, round(xf), round(xa))


def test_strength_without_matches_is_league_mean():
    games = [g(1, "a", "b", 2.0, 1.0), g(1, "b", "a", 1.0, 2.0, False)]
    st = strengths(games, ["a", "b", "c"])
    assert st["c"]["att"] == 1.0 and st["c"]["def"] == 1.0 and st["c"]["n"] == 0
    assert st["a"]["att"] > 1.0 and st["a"]["def"] < 1.0


def test_recent_form_weighs_30_percent():
    games = [g(md, "a", "b", 1.0, 1.0) for md in range(1, 6)] + [g(md, "a", "b", 3.0, 1.0) for md in range(6, 11)]
    games += [g(md, "b", "a", 1.0, 1.0, False) for md in range(1, 11)]
    st = strengths(games, ["a", "b"])
    # Saison 2.0 pro Spiel, letzte 5: 3.0 → 0.7·2 + 0.3·3 = 2.3
    assert st["a"]["xgf"] == pytest.approx(2.3)


def test_expected_goals_uses_means_and_strengths():
    st = {"h": {"att": 1.2, "def": 0.8, "n": 9}, "a": {"att": 0.9, "def": 1.1, "n": 9}}
    lh, la = expected_goals("h", "a", st, Means(1.7, 1.3))
    assert lh == pytest.approx(1.7 * 1.2 * 1.1) and la == pytest.approx(1.3 * 0.9 * 0.8)


def test_calibration_recovers_home_advantage():
    rnd = random.Random(7)

    def pois(lam):
        k, p, L = 0, 1.0, math.exp(-lam)
        while True:
            p *= rnd.random()
            if p < L:
                return k
            k += 1

    results = [(pois(1.7), pois(1.3)) for _ in range(3000)]
    cal = fit_calibration(results)
    assert cal["home"] == pytest.approx(1.7, abs=0.08) and cal["away"] == pytest.approx(1.3, abs=0.08)
    assert -0.2 <= cal["rho"] <= 0.05

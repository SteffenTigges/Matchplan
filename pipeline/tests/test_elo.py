import pytest

from matchplan_data.elo import expected, game_rows, run_elo


def row(date, h, a, hg, ag, div="D1"):
    return {"Div": div, "Date": date, "HomeTeam": h, "AwayTeam": a, "FTHG": str(hg), "FTAG": str(ag)}


def test_expected_home_advantage():
    assert expected(1500, 1500) == pytest.approx(1 / (1 + 10 ** (-65 / 400)))
    assert expected(1600, 1500) > expected(1500, 1500)


def test_game_rows_sorted_and_parsed():
    rows = [row("20/08/2017", "A", "B", 1, 0), row("19/08/17", "C", "D", 2, 2, "D2"), {"Div": "D1", "Date": "", "HomeTeam": "X"}]
    g = game_rows(rows)
    assert [x[1] for x in g] == ["C", "A"] and g[0][5] == "D2"


def test_winner_gains_loser_loses_and_sum_constant():
    r = run_elo(game_rows([row("01/08/2020", "A", "B", 3, 0)]))
    assert r["A"] > 1500 > r["B"] and r["A"] + r["B"] == pytest.approx(3000)


def test_second_division_starts_lower_and_margin_counts():
    r = run_elo(game_rows([row("01/08/2020", "A", "B", 1, 0), row("01/08/2020", "C", "D", 1, 0, "D2")]))
    assert r["C"] < r["A"] and r["D"] < r["B"]
    big = run_elo(game_rows([row("01/08/2020", "A", "B", 5, 0)]))
    small = run_elo(game_rows([row("01/08/2020", "A", "B", 1, 0)]))
    assert big["A"] > small["A"]


def test_base_ratings_continue():
    base = {"A": 1700.0, "B": 1400.0}
    r = run_elo(game_rows([row("01/08/2026", "A", "B", 0, 1)]), base=base)
    assert r["A"] < 1700 and r["B"] > 1400

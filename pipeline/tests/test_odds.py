from pathlib import Path

import pytest

from matchplan_data.odds import closing_odds, implied, odds_by_pair, parse_csv, results

CSV = (Path(__file__).parent / "fixtures" / "footballdata.csv").read_bytes().decode("utf-8")


def test_parses_csv_with_bom():
    rows = parse_csv(CSV)
    assert rows[0]["Div"] == "D1" and rows[0]["HomeTeam"] == "Bayern Munich"
    assert all(r.get("Div") for r in rows)  # Leerzeile entfernt


def test_implied_probabilities_sum_to_one():
    p = implied(1.42, 5.1, 6.8)
    assert sum(p) == pytest.approx(1) and p[0] > p[1] > p[2]


def test_unknown_team_is_skipped():
    odds, unknown = odds_by_pair(parse_csv(CSV))
    assert ("FCB", "BVB") in odds
    assert "Wolfsburg" in unknown and "Arsenal" not in unknown  # nur D1
    assert all("Wolfsburg" not in str(k) for k in odds)


def test_fallback_to_b365():
    odds, _ = odds_by_pair(parse_csv(CSV))
    p = odds[("SGE", "BMG")]
    assert p["source"] == "Bet365" and sum((p["home"], p["draw"], p["away"])) == pytest.approx(1)
    assert odds[("FCB", "BVB")]["source"] == "Schnitt der Buchmacher"


def test_closing_odds_and_results():
    close, _ = closing_odds(parse_csv(CSV))
    assert close[("FCB", "BVB")]["home"] == pytest.approx(implied(1.38, 5.2, 7.5)[0])
    assert ("KOE", "SCP") in close  # ohne Schlussquote → Eröffnungsschnitt
    assert results(parse_csv(CSV)) == [(3, 1), (1, 1), (0, 2)]

from pathlib import Path

from matchplan_data.ligainsider import parse_lineup_page

FIX = Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_parses_gladbach_lineup():
    lu = parse_lineup_page(fixture("ligainsider_bmg.html"))
    assert lu.team == "Borussia Mönchengladbach" and lu.formation == "3-4-3" and lu.home is True
    assert lu.opponent == "Borussia Dortmund"
    assert sum(len(r) for r in lu.rows) == 11 and lu.rows[0][0].player.name == "Nicolas"
    herold = lu.rows[2][3]
    assert herold.player.id == "david-herold_34927" and herold.player.photo.endswith("david-herold-gladbach-2627.jpg")
    assert [a.name for a in herold.alternatives] == ["Castrop"]
    assert herold.alternatives[0].photo.endswith("jens-castrop-gladbach-2627.jpg")


def test_parses_update_label():
    assert parse_lineup_page(fixture("ligainsider_bmg.html")).updated_label == "Gestern | 17.11.2026 21:02"


def test_parses_missing_players():
    lu = parse_lineup_page(fixture("ligainsider_bmg.html"))
    assert lu.missing[0] == {"name": "Kō Itakura", "kind": "Gelb-Rote Karte", "note": "Sperre"}
    assert len(lu.missing) == 6
    assert "­" not in "".join(m["note"] for m in lu.missing)


def test_page_without_lineup_returns_none():
    assert parse_lineup_page("<html><title>Adblocker erkannt</title></html>") is None

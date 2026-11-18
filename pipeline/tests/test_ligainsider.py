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


def test_diagnose_names_the_missing_part():
    from matchplan_data.ligainsider import diagnose

    assert diagnose("<html><title>Adblocker erkannt</title></html>").startswith("Titel ohne 'Voraussichtliche Aufstellung'")
    page = fixture("ligainsider_bmg.html")
    assert diagnose(page) == "ok"
    broken = page.replace("VORAUSSICHTLICHE AUFSTELLUNG", "XXX")
    assert diagnose(broken).startswith("Abschnitt 'VORAUSSICHTLICHE AUFSTELLUNG' fehlt")
    one_missing = page.replace('class="player_position_column', 'class="x', 1)
    assert diagnose(one_missing).startswith("10 Spieler statt 11")


def test_opponent_keeps_digits_in_name():
    page = fixture("ligainsider_bmg.html").replace("Borussia Dortmund", "SV 07 Elversberg")
    assert parse_lineup_page(page).opponent == "SV 07 Elversberg"


def test_parses_page_with_relative_links_as_served_to_scripts():
    """Ligainsider liefert relative Links; Browser-Werkzeuge machen sie absolut."""
    raw = fixture("ligainsider_bmg.html").replace('href="https://www.ligainsider.de/', 'href="/')
    raw = raw.replace('<img class="img-circle" src="https://cdn.ligainsider.de/', '<img alt="" class="img-circle" data-src="https://cdn.ligainsider.de/')
    lu = parse_lineup_page(raw)
    assert lu is not None and sum(len(r) for r in lu.rows) == 11
    herold = lu.rows[2][3]
    assert herold.player.id == "david-herold_34927" and herold.player.photo.endswith("david-herold-gladbach-2627.jpg")
    assert [a.name for a in herold.alternatives] == ["Castrop"]
    assert lu.missing[0]["name"] == "Kō Itakura"


def test_relative_photo_paths_become_absolute():
    raw = fixture("ligainsider_bmg.html").replace('src="https://cdn.ligainsider.de/images/player', 'src="/images/player')
    assert parse_lineup_page(raw).rows[0][0].player.photo.startswith("https://www.ligainsider.de/images/player")

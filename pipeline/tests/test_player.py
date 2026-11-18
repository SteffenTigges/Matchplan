import json
from pathlib import Path

from matchplan_data.fotmob import parse_player

FIX = Path(__file__).parent / "fixtures"


def load():
    return json.loads((FIX / "fotmob_player.json").read_text(encoding="utf-8"))


def test_parses_bio():
    p = parse_player(load())
    assert p["id"] == 1219540 and p["name"] == "Fisnik Asllani" and p["team"] == "TSG"
    assert p["birth_date"] == "2002-08-08" and p["age"] == 24 and p["height_cm"] == 191
    assert p["foot"] == "beidfüßig" and p["country"] == "Kosovo" and p["shirt"] == 11
    assert p["market_value"] == 33943829 and p["contract_end"] == "2029-06-30"
    assert p["positions"][0] == {"label": "Stürmer", "short": "ST", "main": True}


def test_parses_stats_with_percentiles():
    st = parse_player(load())["stats"]
    xg = next(s for s in st if s["key"] == "expected_goals")
    assert xg["group"] == "Abschluss" and xg["title"] == "xG" and xg["value"] == 2.42
    assert round(xg["per90"], 2) == 0.55 and round(xg["pct"]) == 87


def test_parses_career_sections():
    c = parse_player(load())["career"]
    assert c["youth"][-1]["team"] == "1. FC Union Berlin Under 17" and c["youth"][-1]["goals"] == 23
    assert c["senior"][0]["team"] == "Hoffenheim" and c["senior"][1]["kind"] == "Leihe"
    assert c["national"][0]["team"] == "Kosovo"
    assert len(c["national_youth"]) == 2


def test_career_open_end():
    c = parse_player(load())["career"]
    assert c["senior"][0]["end"] is None and c["senior"][0]["start"] == "2025-07-01"


def test_parses_transfers():
    t = parse_player(load())["transfers"][0]
    assert t == {"from": "Hoffenheim", "to": "Elversberg", "date": "2024-07-23", "fee": "Leihe", "loan": True}


def test_player_without_stats():
    d = load()
    d["props"]["pageProps"]["data"].pop("firstSeasonStats")
    d["props"]["pageProps"]["data"].pop("traits")
    p = parse_player(d)
    assert p["stats"] == [] and p["traits"] is None and p["name"] == "Fisnik Asllani"


def test_primary_team_outside_bundesliga():
    d = load()
    d["props"]["pageProps"]["data"]["primaryTeam"] = {"teamId": 10011, "teamName": "Austria Wien"}
    p = parse_player(d)
    assert p["team"] is None and p["team_name"] == "Austria Wien"

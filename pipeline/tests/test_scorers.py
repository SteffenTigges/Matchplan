import math

import pytest

from matchplan_data.scorers import absence_factors, match_player, player_season, scorers

FM = [
    {"id": 1, "name": "Jonas Urbig", "minutes": 900, "xg": 0.0, "keeper": True},
    {"id": 2, "name": "Harry Kane", "minutes": 900, "xg": 9.0, "keeper": False},
    {"id": 3, "name": "Luis Díaz", "minutes": 800, "xg": 4.0, "keeper": False},
    {"id": 4, "name": "Josip Stanišić", "minutes": 700, "xg": 0.5, "keeper": False},
    {"id": 5, "name": "Lennart Karl", "minutes": 120, "xg": 0.6, "keeper": False},
]


def test_matches_player_by_slug():
    assert match_player({"id": "luis-diaz_123", "name": "Díaz"}, FM)["id"] == 3
    assert match_player({"id": "josip-stanisic_9", "name": "Stanisic"}, FM)["id"] == 4
    assert match_player({"name": "Harry Kane"}, FM)["id"] == 2  # Ausfallliste: nur Name


def test_ambiguous_or_unknown_is_none():
    two = FM + [{"id": 9, "name": "Kevin Kane", "minutes": 10, "xg": 0, "keeper": False}]
    assert match_player({"name": "Kane"}, two) is None
    assert match_player({"id": "max-muster_1", "name": "Muster"}, FM) is None


def test_player_season_sums_matches():
    files = [{"season": "2026", "players": [{"id": 2, "team": "FCB", "name": "Harry Kane", "minutes": 90, "xg": 1.0, "keeper": False}]},
             {"season": "2026", "players": [{"id": 2, "team": "FCB", "name": "Harry Kane", "minutes": 80, "xg": 0.5, "keeper": False},
                                            {"id": 7, "team": "BVB", "name": "X", "minutes": 0, "xg": None}]}]
    ps = player_season(files, "2026")
    assert ps["FCB"] == [{"id": 2, "name": "Harry Kane", "minutes": 170, "xg": 1.5, "keeper": False}]
    assert "BVB" not in ps


def slot(pid, name, alts=()):
    return {"player": {"id": pid, "name": name, "photo": ""}, "alternatives": [{"id": a, "name": a.split("_")[0], "photo": ""} for a in alts]}


LINEUP = {"rows": [[slot("jonas-urbig_1", "Urbig")], [slot("josip-stanisic_9", "Stanisic")],
                   [slot("luis-diaz_3", "Díaz", alts=["lennart-karl_5"])], [slot("harry-kane_2", "Kane")], [slot("max-muster_1", "Muster")]]}


def test_alternative_splits_minutes():
    out = {s["name"]: s for s in scorers(LINEUP, FM, team_xg_pg=2.5, lam=2.5, pos={})}
    assert out["Díaz"]["minutes"] == 45 and out["lennart-karl"]["minutes"] == 35
    assert out["Kane"]["minutes"] == 80


def test_unmatched_player_gets_prior():
    out = {s["name"]: s for s in scorers(LINEUP, FM, team_xg_pg=2.5, lam=2.5, pos={})}
    assert out["Muster"]["fm_id"] is None and out["Muster"]["p"] > 0
    assert out["Urbig"]["p"] == 0  # Torwart


def test_scorer_probability_formula():
    out = {s["name"]: s for s in scorers(LINEUP, FM, team_xg_pg=2.5, lam=2.5, pos={})}
    share = (9.0 / 900 * 90) / 2.5
    assert out["Kane"]["p"] == pytest.approx(1 - math.exp(-2.5 * 0.97 * share * 80 / 90), abs=1e-6)


def test_scorer_lambdas_do_not_exceed_team():
    many = {"rows": [[slot(f"harry-kane_{i}", "Kane")] for i in range(11)]}
    lam = 1.2
    total = sum(s["lam"] for s in scorers(many, FM, team_xg_pg=0.5, lam=lam, pos={}))
    assert total <= 0.97 * lam + 1e-9


def test_absence_factor_capped():
    team = FM + [{"id": 10 + i, "name": f"Stamm Spieler{c}", "minutes": 900, "xg": 0.1, "keeper": False} for i, c in enumerate("abc")]
    missing = [{"name": n["name"]} for n in team] + [{"name": "Unbekannt Spieler"}]
    att, dfn, info = absence_factors(missing, team)
    assert att == 0.75 and dfn == 1.25
    assert [i["name"] for i in info if i["fm_id"] is None] == ["Unbekannt Spieler"]


def test_no_absences_neutral():
    assert absence_factors([], FM)[:2] == (1.0, 1.0)


def test_unmatched_prior_follows_lineup_row():
    lu = {"rows": [[slot("a-tor_1", "Tor")], [slot("b-abwehr_1", "Abwehr")], [slot("c-mitte_1", "Mitte")], [slot("d-sturm_1", "Sturm")]]}
    out = {s["name"]: s["p"] for s in scorers(lu, FM, team_xg_pg=2.0, lam=2.0, pos={})}
    assert out["Sturm"] > out["Mitte"] > out["Abwehr"] > out["Tor"] == 0


def test_build_links_maps_lineup_and_names():
    from matchplan_data.scorers import build_links
    lineups = {"FCB": {"rows": [[slot("harry-kane_2", "Kane", alts=["luis-diaz_3"])], [slot("max-muster_1", "Muster")]]}}
    rows = [{"id": 2, "team": "FCB", "name": "Harry Kane"}, {"id": 3, "team": "FCB", "name": "Luis Díaz"}]
    links = build_links(lineups, rows)
    assert links["li"] == {"harry-kane_2": 2, "luis-diaz_3": 3}
    assert links["names"]["FCB"] == {"harry kane": 2, "luis diaz": 3}

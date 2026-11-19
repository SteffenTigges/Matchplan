import pytest

from matchplan_data.scouting import (build_report, formation_usage, key_players, last_load, matchplan_rules, minute_bands,
                                     reaction, situation_split, strengths_weaknesses)


def shot(team, sit, xg, goal=False):
    return {"team": team, "situation": sit, "xg": xg, "result": "goal" if goal else "miss", "own_goal": False}


def test_situation_split():
    shots = [shot("A", "RegularPlay", 0.3, True), shot("A", "FastBreak", 0.4, True), shot("A", "FromCorner", 0.1),
             shot("A", "Penalty", 0.79, True), shot("B", "RegularPlay", 0.5, True)]
    s = situation_split([shots], "A")
    assert s["Spielaufbau"]["goals"] == 1 and s["Konter"]["goals"] == 1 and s["Elfmeter"]["goals"] == 1
    assert s["Standard"]["shots"] == 1 and s["Standard"]["xg"] == pytest.approx(0.1)
    assert sum(v["share"] for v in s.values()) == pytest.approx(1.0, abs=0.005)
    against = situation_split([shots], "A", against=True)
    assert against["Spielaufbau"]["goals"] == 1 and against["Konter"]["goals"] == 0


def test_minute_bands():
    b = minute_bands([3, 15, 16, 45, 46, 93, 76, None])
    assert b == [2, 1, 1, 1, 0, 2]


def test_formation_usage():
    files = [({"home": "A", "away": "B"}, {"lineups": {"home": {"formation": "4-2-3-1"}, "away": {"formation": "3-5-2"}}}),
             ({"home": "B", "away": "A"}, {"lineups": {"home": {"formation": "4-4-2"}, "away": {"formation": "4-2-3-1"}}}),
             ({"home": "A", "away": "C"}, {"lineups": {"home": {"formation": "4-4-2"}, "away": None}}),
             ({"home": "A", "away": "D"}, {"lineups": None})]
    assert formation_usage(files, "A") == [{"formation": "4-2-3-1", "games": 2}, {"formation": "4-4-2", "games": 1}]


def m(home, away, score, ht, goals):
    return {"home": home, "away": away, "finished": True, "score": score, "halftime": ht,
            "goals": [{"minute": mi, "team": t, "own_goal": False, "penalty": False, "scorer": ""} for mi, t in goals]}


def test_comeback_points_from_goal_order():
    games = [m("A", "B", [2, 1], [0, 1], [(10, "B"), (60, "A"), (90, "A")]),   # Rückstand gedreht: +3
             m("C", "A", [1, 1], [0, 1], [(20, "A"), (80, "C")]),               # Führung verspielt: 2 Punkte weg
             m("A", "D", [0, 0], [0, 0], [])]
    r = reaction(games, "A")
    assert r["points_from_behind"] == 3 and r["points_dropped"] == 2
    assert r["ht_trail"] == {"games": 1, "points": 3} and r["ht_lead"] == {"games": 1, "points": 1}
    assert r["late_for"] == 1 and r["late_against"] == 1 and r["goals_for"] == 3 and r["goals_against"] == 2


def test_team_without_matches():
    rep = build_report("A", [], {}, {"metrics": [], "teams": {}}, [], lambda pid: None, None, None)
    assert rep["team"] == "A" and rep["matches"] == 0
    assert rep["scoring"]["situations"] is None and rep["matchplan"] == [] and rep["key_players"] == []


FM_P = lambda pid, team, mins, xg=0.0, xa=0.0, rating=7.0, name=None: {"id": pid, "team": team, "name": name or f"P{pid}", "minutes": mins, "xg": xg, "xa": xa, "rating": rating, "goals": 0, "assists": 0}


def test_key_players_need_minutes():
    files = [({"home": "A", "away": "B"}, {"matchday": 1, "players": [FM_P(1, "A", 500, 2.0, 1.0), FM_P(2, "A", 300, 3.0), FM_P(3, "A", 900, 0.5, 0.2, 7.4)]})]
    index = {1: {"pos": "ST"}, 3: {"pos": "CB"}}
    prof = {1: {"stats": [{"title": "Tore", "pct": 95}, {"title": "Pässe", "pct": 40}, {"title": "xG", "pct": 90}]}}
    kp = key_players(files, "A", index, prof.get)
    assert [p["id"] for p in kp] == [1, 3]
    assert kp[0]["why"] == ["Tore (95. Perzentil)", "xG (90. Perzentil)"] and kp[1]["why"] == []


def test_load_last_three():
    files = [({"home": "A", "away": "B"}, {"matchday": md, "players": [FM_P(1, "A", 90), FM_P(2, "A", 30 if md == 3 else 90)]}) for md in (1, 2, 3, 4)]
    load = last_load(files, "A")
    assert load[0] == {"id": 1, "name": "P1", "minutes": 270, "full": True}
    assert load[1]["minutes"] == 210 and load[1]["full"] is False


TS = {"metrics": [{"key": "xg_pg", "label": "xG pro Spiel", "higher_is_better": True, "fmt": "dec2"},
                  {"key": "ppda", "label": "PPDA", "higher_is_better": False, "fmt": "dec1"},
                  {"key": "xga_setplay_pg", "label": "Zugelassene xG nach Standards", "higher_is_better": False, "fmt": "dec2"},
                  {"key": "aerial_rate", "label": "Luftzweikämpfe gewonnen", "higher_is_better": True, "fmt": "pct"},
                  {"key": "possession", "label": "Ballbesitz", "higher_is_better": True, "fmt": "pct"}],
      "teams": {"A": {"matches": 9, "xg_pg": {"value": 2.1, "rank": 2}, "ppda": {"value": 8.0, "rank": 1},
                      "xga_setplay_pg": {"value": 0.5, "rank": 17}, "aerial_rate": {"value": None, "rank": None},
                      "possession": {"value": 0.58, "rank": 3}}}}


def test_strengths_and_weaknesses_from_ranks():
    s, w = strengths_weaknesses(TS, "A")
    assert [x["label"] for x in s] == ["PPDA", "xG pro Spiel", "Ballbesitz"]
    assert [x["label"] for x in w] == ["Zugelassene xG nach Standards"]


def test_rules_need_data():
    rules = matchplan_rules(TS, "A", {"late_against": 0, "goals_against": 0}, None, None)
    keys = [r["key"] for r in rules]
    assert "setpieces" in keys and "press" in keys and "aerial" not in keys


def test_rule_evidence_present():
    rules = matchplan_rules(TS, "A", {"late_against": 4, "goals_against": 10}, {"left": 45, "center": 20, "right": 35}, None)
    assert {r["key"] for r in rules} >= {"setpieces", "late", "side"}
    for r in rules:
        assert r["text"] and r["evidence"] and all("label" in e and "value" in e for e in r["evidence"])

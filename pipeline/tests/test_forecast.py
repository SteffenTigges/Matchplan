import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from matchplan_data.forecast import run_forecast
from matchplan_data.odds import FIXTURES_URL

CSV = (Path(__file__).parent / "fixtures" / "footballdata.csv").read_bytes().decode("utf-8")
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
AT = NOW.isoformat(timespec="seconds")


def match(mid, home, away, kickoff, score=None):
    return {"id": mid, "kickoff": kickoff, "home": home, "away": away, "finished": score is not None,
            "score": score, "halftime": None, "goals": []}


def fm_file(out, mid, md, xg, home_names=(), players=()):
    d = {"season": 2026, "oldb_id": mid, "matchday": md, "stats": {"expected_goals": list(xg)},
         "lineups": {"home": {"players": [{"name": n} for n in home_names]}, "away": {"players": []}},
         "players": list(players)}
    (out / "fotmob").mkdir(parents=True, exist_ok=True)
    (out / "fotmob" / f"{mid}.json").write_text(json.dumps(d))


def slot(pid, name):
    return {"player": {"id": pid, "name": name, "photo": "p.jpg"}, "alternatives": []}


LINEUP_SGE = {"rows": [[slot("kevin-trapp_1", "Trapp")], [slot("hugo-ekitike_2", "Ekitiké")]],
              "missing": [{"name": "Mario Götze", "kind": "Verletzung"}], "formation": "4-4-2"}
KANE = {"id": 2, "team": "SGE", "name": "Hugo Ekitiké", "minutes": 90, "xg": 0.9, "keeper": False}


def setup(tmp_path, md2_score=None):
    md = {1: [match(1, "FCB", "BVB", "2026-11-14T14:30:00Z", [3, 1]), match(2, "SGE", "BMG", "2026-11-14T14:30:00Z", [1, 1])],
          2: [match(3, "SGE", "BVB", "2026-11-21T14:30:00Z", md2_score), match(4, "BMG", "FCB", "2026-11-20T10:00:00Z")]}
    fm_file(tmp_path, 1, 1, (2.5, 0.7))
    fm_file(tmp_path, 2, 1, (1.2, 1.0), players=[KANE])
    return md


BIG = CSV + "\n".join(CSV.splitlines()[1:4] * 150)  # genug Vorsaison-Spiele für die Kalibrierung


def fake_get(fail=()):
    def get(url):
        if any(f in url for f in fail):
            raise RuntimeError("HTTP 503")
        return BIG if "mmz4281" in url else CSV
    return get


def read(p):
    return json.loads(Path(p).read_text())


def test_writes_predictions_for_current_matchday(tmp_path):
    md = setup(tmp_path)
    status = {}
    run_forecast(tmp_path, fake_get(), md, 2, {"SGE": LINEUP_SGE}, NOW, AT, status)
    pred = read(tmp_path / "predictions" / "2.json")
    p = pred["matches"]["3"]
    assert sum(p["probs"]) == pytest.approx(1, abs=1e-3)
    assert len(p["tip"]) == 2 and len(p["matrix"]) == 6
    assert p["scorers"]["home"][0]["name"] == "Ekitiké" and p["scorers"]["away"] == []
    assert p["xi"]["home"] == [{"li_id": "kevin-trapp_1", "name": "Trapp"}, {"li_id": "hugo-ekitike_2", "name": "Ekitiké"}]
    assert p["why"]["absences"]["home"][0]["name"] == "Mario Götze"
    assert "4" not in pred["matches"]  # schon angepfiffen, keine nachträgliche Prognose
    assert status["prognose"]["ok"]


def test_started_match_prediction_is_frozen(tmp_path):
    md = setup(tmp_path)
    (tmp_path / "predictions").mkdir()
    (tmp_path / "predictions" / "2.json").write_text(json.dumps({"matchday": 2, "matches": {"4": {"marker": True}}}))
    run_forecast(tmp_path, fake_get(), md, 2, {}, NOW, AT, {})
    pred = read(tmp_path / "predictions" / "2.json")
    assert pred["matches"]["4"] == {"marker": True} and "3" in pred["matches"]


def test_walk_forward_uses_only_earlier_matchdays(tmp_path):
    md = setup(tmp_path, md2_score=[0, 4])
    fm_file(tmp_path, 3, 2, (0.2, 3.5))
    run_forecast(tmp_path, fake_get(), md, 2, {}, NOW, AT, {})
    first = {g["id"]: g for g in read(tmp_path / "model.json")["check"]["games"]}
    fm_file(tmp_path, 3, 2, (3.0, 0.1))  # andere Werte am 2. Spieltag ändern dessen Prüfprognose nicht
    run_forecast(tmp_path, fake_get(), md, 2, {}, NOW, AT, {})
    second = {g["id"]: g for g in read(tmp_path / "model.json")["check"]["games"]}
    assert first[3]["probs"] == second[3]["probs"]
    assert first[1]["probs"] == pytest.approx(first[2]["probs"])  # 1. Spieltag: nur Ligaschnitt
    check = read(tmp_path / "model.json")["check"]
    assert check["matches"] == 3 and 0 <= check["tendency_rate"] <= 1 and check["brier"] > 0


def test_odds_missing_keeps_prediction(tmp_path):
    md = setup(tmp_path)
    status = {}
    run_forecast(tmp_path, fake_get(fail=[FIXTURES_URL]), md, 2, {}, NOW, AT, status)
    assert read(tmp_path / "predictions" / "2.json")["matches"]["3"]["odds"] is None
    assert status["quoten"]["ok"] is False and status["prognose"]["ok"]


def test_odds_attached_when_available(tmp_path):
    md = setup(tmp_path)
    md[2][0] = match(3, "SGE", "BMG", "2026-11-21T14:30:00Z")
    run_forecast(tmp_path, fake_get(), md, 2, {}, NOW, AT, {})
    assert read(tmp_path / "predictions" / "2.json")["matches"]["3"]["odds"]["source"] == "Bet365"


def test_lineup_hits_after_match(tmp_path):
    md = setup(tmp_path)
    (tmp_path / "predictions").mkdir()
    xi = [{"li_id": "kevin-trapp_1", "name": "Trapp"}, {"li_id": "hugo-ekitike_2", "name": "Ekitiké"}]
    (tmp_path / "predictions" / "1.json").write_text(json.dumps({"matchday": 1, "matches": {"2": {"xi": {"home": xi, "away": []}}}}))
    fm_file(tmp_path, 2, 1, (1.2, 1.0), home_names=["Kevin Trapp", "Rasmus Kristensen"])
    run_forecast(tmp_path, fake_get(), md, 2, {}, NOW, AT, {})
    hits = read(tmp_path / "predictions" / "1.json")["matches"]["2"]["lineup_hits"]
    assert hits == {"home": 1, "away": None}


def test_calibration_is_cached_for_a_week(tmp_path):
    md = setup(tmp_path)
    calls = []

    def get(url):
        calls.append(url)
        return fake_get()(url)

    run_forecast(tmp_path, get, md, 2, {}, NOW, AT, {})
    n = sum("mmz4281/2" in u and "2627" not in u for u in calls)
    calls.clear()
    run_forecast(tmp_path, get, md, 2, {}, NOW, AT, {})
    assert n == 3 and not any("mmz4281/2" in u and "2627" not in u for u in calls)


def test_failed_calibration_keeps_defaults_and_reports(tmp_path):
    md = setup(tmp_path)
    status = {}
    run_forecast(tmp_path, lambda u: CSV, md, 2, {}, NOW, AT, status)  # nur 3 Spiele: zu wenig
    cal = read(tmp_path / "model.json")["calibration"]
    assert cal["rho"] == -0.05 and "Kalibrierung" in status["prognose"]["error"]

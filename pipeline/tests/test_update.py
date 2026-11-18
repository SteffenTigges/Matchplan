import json
from datetime import datetime, timezone
from pathlib import Path

from matchplan_data.probe import Response
from matchplan_data.teams import team_by_key
from matchplan_data.update import run_update

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)


def fake(broken=()):
    pages = {
        "https://api.openligadb.de/getmatchdata/bl1/2026/9": (FIX / "openligadb_md9.json").read_text(encoding="utf-8"),
        "https://api.openligadb.de/getmatchdata/bl1/2026/10": (FIX / "openligadb_md10.json").read_text(encoding="utf-8"),
        "https://api.openligadb.de/getbltable/bl1/2026": (FIX / "openligadb_table.json").read_text(encoding="utf-8"),
        team_by_key("BMG").li_url: (FIX / "ligainsider_bmg.html").read_text(encoding="utf-8"),
    }

    def fetch(url):
        if url in broken:
            return Response(500, "", "text/html", 1)
        if url.startswith("https://api.openligadb.de/getmatchdata/"):
            return Response(200, pages.get(url, "[]"), "application/json", 1)
        if url in pages:
            return Response(200, pages[url], "text/html", 1)
        return Response(500, "", "text/html", 1)

    return fetch


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_writes_season_table_matchdays_and_lineups(tmp_path):
    status = run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    season = read(tmp_path / "season.json")
    assert season["current_matchday"] == 10 and season["season"] == 2026
    assert season["teams"]["BMG"]["crest"] == "https://cdn.ligainsider.de/images/teams/medium/borussia-moenchengladbach-wappen.png"
    assert read(tmp_path / "table.json")["rows"][0]["team"] == "FCB"
    assert read(tmp_path / "matchdays" / "9.json")["matches"][0]["score"] == [2, 1]
    lu = read(tmp_path / "lineups" / "current.json")
    assert lu["matchday"] == 10 and lu["teams"]["BMG"]["formation"] == "3-4-3"
    assert lu["teams"]["BMG"]["fetched_at"] == "2026-11-18T16:00:00+00:00"
    assert status["openligadb"]["ok"] is True and status["ligainsider:BMG"]["ok"] is True
    assert status["ligainsider:FCB"]["ok"] is False
    assert read(tmp_path / "status" / "sources.json") == status


def test_failed_lineup_keeps_previous_file(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    before = read(tmp_path / "lineups" / "current.json")["teams"]["BMG"]
    status = run_update(tmp_path, fake(broken={team_by_key("BMG").li_url}), NOW, sleep=lambda s: None)
    assert read(tmp_path / "lineups" / "current.json")["teams"]["BMG"] == before
    assert status["ligainsider:BMG"]["ok"] is False


def test_second_identical_run_adds_no_history(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    first = read(tmp_path / "lineups" / "history-2026-10.json")["events"]
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    assert read(tmp_path / "lineups" / "history-2026-10.json")["events"] == first
    assert [e["kind"] for e in first] == ["first"]


def test_failed_openligadb_keeps_previous_matchday(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    status = run_update(tmp_path, fake(broken={"https://api.openligadb.de/getmatchdata/bl1/2026/10"}), NOW, sleep=lambda s: None)
    assert len(read(tmp_path / "matchdays" / "10.json")["matches"]) == 2
    assert status["openligadb"]["ok"] is False


def test_first_run_with_openligadb_down_writes_no_season_or_lineups(tmp_path):
    def down(url):
        if "openligadb" in url:
            return Response(503, "", "text/plain", 1)
        return fake()(url)

    status = run_update(tmp_path, down, NOW, sleep=lambda s: None)
    assert not (tmp_path / "season.json").exists()
    assert not (tmp_path / "lineups" / "current.json").exists()
    assert status["openligadb"]["ok"] is False


def test_recently_finished_matchday_is_fetched_again(tmp_path):
    calls = []
    base = fake()

    def counting(url):
        calls.append(url)
        return base(url)

    run_update(tmp_path, counting, NOW, sleep=lambda s: None)
    calls.clear()
    soon = datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)  # Spieltag 9 erst seit kurzem beendet
    run_update(tmp_path, counting, soon, sleep=lambda s: None)
    assert "https://api.openligadb.de/getmatchdata/bl1/2026/9" in calls
    calls.clear()
    run_update(tmp_path, counting, NOW, sleep=lambda s: None)  # 10 Tage später: Spieltag 9 bleibt liegen
    assert "https://api.openligadb.de/getmatchdata/bl1/2026/9" not in calls


def test_lineup_for_another_game_is_not_stored(tmp_path):
    def wrong_game(url):
        r = fake()(url)
        if url == team_by_key("BMG").li_url:
            return Response(200, r.text.replace("Borussia Dortmund", "1. FC Köln"), "text/html", 1)
        return r

    status = run_update(tmp_path, wrong_game, NOW, sleep=lambda s: None)
    assert "BMG" not in read(tmp_path / "lineups" / "current.json")["teams"]
    assert "anderes Spiel" in status["ligainsider:BMG"]["error"]


def test_files_carry_the_season(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    assert read(tmp_path / "matchdays" / "9.json")["season"] == 2026
    assert (tmp_path / "lineups" / "history-2026-10.json").exists()


def test_matchday_files_of_another_season_are_refetched(tmp_path):
    (tmp_path / "matchdays").mkdir(parents=True)
    (tmp_path / "matchdays" / "9.json").write_text(json.dumps({"matchday": 9, "season": 2025, "matches": [
        {"id": 1, "kickoff": "2025-11-01T14:30:00Z", "home": "FCB", "away": "BVB", "finished": True, "score": [1, 0], "halftime": [0, 0], "goals": []}]}), encoding="utf-8")
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    assert read(tmp_path / "matchdays" / "9.json")["matches"][0]["home"] == "BVB"

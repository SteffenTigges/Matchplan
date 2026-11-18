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
    first = read(tmp_path / "lineups" / "history-10.json")["events"]
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    assert read(tmp_path / "lineups" / "history-10.json")["events"] == first
    assert [e["kind"] for e in first] == ["first"]


def test_failed_openligadb_keeps_previous_matchday(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    status = run_update(tmp_path, fake(broken={"https://api.openligadb.de/getmatchdata/bl1/2026/10"}), NOW, sleep=lambda s: None)
    assert len(read(tmp_path / "matchdays" / "10.json")["matches"]) == 2
    assert status["openligadb"]["ok"] is False

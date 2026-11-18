import json
from datetime import datetime, timezone
from pathlib import Path

from matchplan_data.probe import Response
from matchplan_data.teams import team_by_key
from matchplan_data.update import run_update

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 11, 18, 16, 0, tzinfo=timezone.utc)


def wrap(name):
    return f'<html><script id="__NEXT_DATA__" type="application/json">{(FIX / name).read_text(encoding="utf-8")}</script></html>'


def fake(broken=()):
    pages = {
        "https://api.openligadb.de/getmatchdata/bl1/2026/9": (FIX / "openligadb_md9.json").read_text(encoding="utf-8"),
        "https://api.openligadb.de/getmatchdata/bl1/2026/10": (FIX / "openligadb_md10.json").read_text(encoding="utf-8"),
        "https://api.openligadb.de/getbltable/bl1/2026": (FIX / "openligadb_table.json").read_text(encoding="utf-8"),
        team_by_key("BMG").li_url: (FIX / "ligainsider_bmg.html").read_text(encoding="utf-8"),
        "https://www.fotmob.com/leagues/54/fixtures/bundesliga": wrap("fotmob_league.json"),
        "https://www.fotmob.com/matches/hoffenheim-vs-schalke-04/2syjsa": wrap("fotmob_match.json"),
        "https://www.fotmob.com/players/173461/x": wrap("fotmob_player.json"),
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


def test_slow_page_is_retried_once(tmp_path):
    base = fake()
    tries = {"n": 0}

    def flaky(url):
        if url == team_by_key("BMG").li_url and tries["n"] == 0:
            tries["n"] += 1
            raise TimeoutError("Read timed out")
        return base(url)

    status = run_update(tmp_path, flaky, NOW, sleep=lambda s: None)
    assert status["ligainsider:BMG"]["ok"] is True


FM_MATCH = "https://www.fotmob.com/matches/hoffenheim-vs-schalke-04/2syjsa"
FM_LEAGUE = "https://www.fotmob.com/leagues/54/fixtures/bundesliga"


def test_writes_fotmob_match_and_teamstats(tmp_path):
    status = run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    fm = read(tmp_path / "fotmob" / "83231.json")
    assert fm["oldb_id"] == 83231 and fm["matchday"] == 9 and fm["season"] == 2026
    assert fm["stats"]["expected_goals"] == [2.23, 2.6] and len(fm["shots"]) == 6
    ts = read(tmp_path / "teamstats.json")
    assert ts["teams"]["TSG"]["xg_pg"]["value"] == 2.23 and ts["teams"]["TSG"]["matches"] == 1
    assert ts["teams"]["TSG"]["points"] == {"value": 3, "rank": 1}
    assert status["fotmob"]["ok"] is True


def test_stored_old_match_is_not_refetched(tmp_path):
    calls = []
    base = fake()

    def counting(url):
        calls.append(url)
        return base(url)

    run_update(tmp_path, counting, NOW, sleep=lambda s: None)
    assert FM_MATCH in calls
    calls.clear()
    run_update(tmp_path, counting, NOW, sleep=lambda s: None)
    assert FM_MATCH not in calls and FM_LEAGUE in calls


def test_unmatched_fotmob_match_is_skipped(tmp_path):
    status = run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    assert sorted(p.name for p in (tmp_path / "fotmob").iterdir()) == ["83231.json"]
    assert "1 Spiel ohne Zuordnung" in status["fotmob"]["note"]


def test_fotmob_down_keeps_previous_files(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    status = run_update(tmp_path, fake(broken={FM_LEAGUE}), NOW, sleep=lambda s: None)
    assert (tmp_path / "fotmob" / "83231.json").exists() and (tmp_path / "teamstats.json").exists()
    assert status["fotmob"]["ok"] is False


def test_incomplete_match_file_is_refetched_within_14_days(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    path = tmp_path / "fotmob" / "83231.json"
    d = read(path)
    d["stats"] = {}
    path.write_text(json.dumps(d), encoding="utf-8")
    calls = []
    base = fake()
    run_update(tmp_path, lambda u: (calls.append(u), base(u))[1], NOW, sleep=lambda s: None)
    assert FM_MATCH in calls and read(path)["stats"]["expected_goals"] == [2.23, 2.6]


def test_warns_when_core_stats_are_missing(tmp_path):
    def renamed(url):
        r = fake()(url)
        if url == FM_MATCH:
            return Response(200, r.text.replace('"expected_goals"', '"xg_renamed"'), "text/html", 1)
        return r

    status = run_update(tmp_path, renamed, NOW, sleep=lambda s: None)
    assert "ohne Kernwerte" in status["fotmob"]["note"]


def test_old_format_match_is_refetched(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    path = tmp_path / "fotmob" / "83231.json"
    d = read(path)
    d.pop("v")
    path.write_text(json.dumps(d), encoding="utf-8")
    calls = []
    base = fake()
    later = datetime(2027, 1, 30, tzinfo=timezone.utc)  # weit nach dem Spiel
    run_update(tmp_path, lambda u: (calls.append(u), base(u))[1], later, sleep=lambda s: None)
    assert FM_MATCH in calls and read(path)["v"] == 2


PLAYER = "https://www.fotmob.com/players/173461/x"


def test_writes_player_profile_and_index(tmp_path):
    status = run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    prof = read(tmp_path / "players" / "173461.json")
    assert prof["name"] == "Fisnik Asllani" and prof["fetched_at"] == "2026-11-18T16:00:00+00:00"
    idx = {p["id"]: p for p in read(tmp_path / "players.json")["players"]}
    assert set(idx) == {173461, 15403}
    assert idx[173461]["team"] == "TSG" and idx[173461]["minutes"] == 70 and idx[173461]["apps"] == 1
    assert idx[173461]["rating"] == 6.31 and idx[173461]["pos"] == "ST" and idx[173461]["age"] == 24
    assert idx[15403]["pos"] is None
    assert "1 von 2 Profilen" in status["fotmob_players"]["note"]


def test_player_fetch_is_capped_and_oldest_first(tmp_path, monkeypatch):
    from matchplan_data import update
    monkeypatch.setattr(update, "PLAYER_CAP", 1)
    calls = []
    base = fake()
    run_update(tmp_path, lambda u: (calls.append(u), base(u))[1], NOW, sleep=lambda s: None)
    assert sum("/players/" in c for c in calls) == 1


def test_fresh_player_is_not_refetched(tmp_path):
    run_update(tmp_path, fake(), NOW, sleep=lambda s: None)
    calls = []
    base = fake()
    run_update(tmp_path, lambda u: (calls.append(u), base(u))[1], NOW, sleep=lambda s: None)
    assert PLAYER not in calls

import json
from datetime import datetime, timezone
from pathlib import Path

from matchplan_data.live import due_matches, run_live
from matchplan_data.probe import Response

LEAGUE = {"props": {"pageProps": {"fixtures": {"allMatches": [
    {"id": "5881230", "pageUrl": "/matches/x#5881230", "round": "10", "home": {"id": "9788"}, "away": {"id": "9789"},
     "status": {"finished": False, "utcTime": "2026-11-21T14:30:00Z"}}]}}}}


def page(status, events):
    nd = {"props": {"pageProps": {"general": {"matchId": "5881230"},
                                  "header": {"teams": [{"score": 1}, {"score": 0}], "status": status},
                                  "content": {"matchFacts": {"events": {"events": events}},
                                              "stats": {"Periods": {"All": {"stats": [{"stats": [{"key": "BallPossesion", "stats": [55, 45]}]}]}}}}}}}
    return '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(nd) + "</script>"


def setup(tmp: Path):
    (tmp / "matchdays").mkdir(parents=True)
    (tmp / "season.json").write_text(json.dumps({"current_matchday": 10}))
    (tmp / "matchdays" / "10.json").write_text(json.dumps({"matches": [
        {"id": 83242, "kickoff": "2026-11-21T14:30:00Z", "home": "BMG", "away": "BVB", "finished": False},
        {"id": 83244, "kickoff": "2026-11-21T17:30:00Z", "home": "S04", "away": "VFB", "finished": False}]}))


def fetcher(status, events=()):
    def f(url):
        if "leagues" in url:
            return Response(200, '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(LEAGUE) + "</script>", "text/html", 0)
        return Response(200, page(status, list(events)), "text/html", 0)
    return f


def test_due_matches_window(tmp_path):
    setup(tmp_path)
    ids = lambda t: [m["id"] for m in due_matches(tmp_path, datetime.fromisoformat(t))]
    assert ids("2026-11-21T15:10:00+00:00") == [83242]
    assert ids("2026-11-21T12:00:00+00:00") == []
    assert ids("2026-11-21T17:25:00+00:00") == [83242, 83244] or ids("2026-11-21T17:25:00+00:00") == [83244]


def test_writes_live_file_and_detects_final_whistle(tmp_path):
    setup(tmp_path)
    now = datetime(2026, 11, 21, 15, 10, tzinfo=timezone.utc)
    goal = {"type": "Goal", "time": 23, "isHome": True, "player": {"id": 5, "name": "Tim Kleindienst"}, "newScore": [1, 0]}
    res = run_live(tmp_path, fetcher({"started": True, "finished": False, "liveTime": {"short": "41'"}}, [goal]), now)
    live = json.loads((tmp_path / "live" / "83242.json").read_text())
    assert res == {"live": 1, "finished_now": [], "errors": []}
    assert live["status"]["minute"] == "41'" and live["events"][0]["player"] == "Tim Kleindienst" and live["stats"]["BallPossesion"] == [55, 45]
    res = run_live(tmp_path, fetcher({"started": True, "finished": True}), datetime(2026, 11, 21, 16, 30, tzinfo=timezone.utc))
    assert res["finished_now"] == [83242]
    res = run_live(tmp_path, fetcher({"started": True, "finished": True}), datetime(2026, 11, 21, 16, 35, tzinfo=timezone.utc))
    assert res["finished_now"] == []  # nur einmal melden


def test_nothing_due_does_not_fetch(tmp_path):
    setup(tmp_path)
    calls = []
    run_live(tmp_path, lambda u: calls.append(u), datetime(2026, 11, 21, 9, 0, tzinfo=timezone.utc))
    assert calls == []

from matchplan_data.probe import ProbeTarget, Response, run_probe


def ok_target(check=lambda r: "MARK" in r.text):
    return ProbeTarget("x", "X", "https://x.test", check, "Test")


def test_ok_when_status_200_and_marker_present():
    res = run_probe([ok_target()], lambda u: Response(200, "..MARK..", "text/html", 12), sleep=lambda s: None)
    assert res[0].ok is True and res[0].status == 200 and res[0].bytes == 8 and res[0].error is None


def test_status_200_without_marker_fails():
    res = run_probe([ok_target()], lambda u: Response(200, "Bitte Cookies akzeptieren", "text/html", 5), sleep=lambda s: None)
    assert res[0].ok is False and res[0].error == "Inhalt unerwartet"


def test_non_200_fails_with_status_in_error():
    res = run_probe([ok_target()], lambda u: Response(403, "MARK", "text/html", 5), sleep=lambda s: None)
    assert res[0].ok is False and res[0].error == "HTTP 403"


def test_exception_is_recorded_not_raised():
    def boom(u):
        raise TimeoutError("timed out")

    res = run_probe([ok_target(), ok_target()], boom, sleep=lambda s: None)
    assert len(res) == 2 and all(r.ok is False for r in res)
    assert res[0].error == "TimeoutError: timed out" and res[0].status is None


def test_pauses_between_requests_not_after_last():
    slept = []
    run_probe([ok_target()] * 3, lambda u: Response(200, "MARK", "text/html", 1), pause_s=2.0, sleep=slept.append)
    assert slept == [2.0, 2.0]


def test_raising_check_counts_as_unexpected_content():
    def bad_check(r):
        raise ValueError("kaputt")

    res = run_probe([ok_target(bad_check)], lambda u: Response(200, "x", "text/html", 1), sleep=lambda s: None)
    assert res[0].ok is False and res[0].error == "Inhalt unerwartet"


# ---------- Task 2: Ziele, Bericht, Kommandozeile ----------
import json
from datetime import datetime, timezone

from matchplan_data import probe
from matchplan_data.probe import TARGETS, ProbeResult, build_report


def test_targets_cover_all_spec_sources():
    assert [t.key for t in TARGETS] == ["openligadb", "fotmob_api", "fotmob_web", "understat", "bundesliga",
                                        "ligainsider", "ligainsider_img", "transfermarkt", "clubelo", "footballdata"]


def test_ligainsider_check_needs_lineup_rows():
    t = next(t for t in TARGETS if t.key == "ligainsider")
    assert t.check(Response(200, 'class="player_position_row"' * 4, "text/html", 1))
    assert not t.check(Response(200, "<html>Adblocker erkannt</html>", "text/html", 1))


def test_openligadb_check_needs_nonempty_json_list():
    t = next(t for t in TARGETS if t.key == "openligadb")
    assert t.check(Response(200, '[{"matchID": 1}]', "application/json", 1))
    assert not t.check(Response(200, "[]", "application/json", 1))


def test_build_report_counts_and_serializes():
    now = datetime(2026, 11, 18, 17, 0, tzinfo=timezone.utc)
    r = [ProbeResult("a", "A", "u", True, 200, 5, 10, None, "p"),
         ProbeResult("b", "B", "u", False, None, None, None, "HTTP 403", "p")]
    rep = build_report(r, now)
    assert rep["checked_at"] == "2026-11-18T17:00:00+00:00" and rep["ok_count"] == 1 and rep["total"] == 2
    assert rep["sources"][1]["error"] == "HTTP 403"


def test_main_writes_report(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "http_fetch", lambda u: Response(500, "", "text/html", 1))
    monkeypatch.setattr(probe.time, "sleep", lambda s: None)
    out = tmp_path / "sub" / "probe.json"
    assert probe.main(["--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["total"] == 10

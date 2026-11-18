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

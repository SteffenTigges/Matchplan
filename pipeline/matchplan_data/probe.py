"""Quellen-Check: prüft, ob jede geplante Datenquelle erreichbar ist und echte Daten liefert."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
TIMEOUT_S = 30


@dataclass(frozen=True)
class Response:
    status: int
    text: str
    content_type: str
    elapsed_ms: int


Fetcher = Callable[[str], Response]


@dataclass(frozen=True)
class ProbeTarget:
    key: str
    name: str
    url: str
    check: Callable[[Response], bool]
    purpose: str


@dataclass
class ProbeResult:
    key: str
    name: str
    url: str
    ok: bool
    status: int | None
    elapsed_ms: int | None
    bytes: int | None
    error: str | None
    purpose: str


def http_fetch(url: str) -> Response:
    started = time.monotonic()
    r = requests.get(
        url,
        timeout=TIMEOUT_S,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"},
    )
    ctype = r.headers.get("Content-Type", "")
    text = "" if ctype.startswith("image/") else r.text
    return Response(r.status_code, text, ctype, int((time.monotonic() - started) * 1000))


def _passes(target: ProbeTarget, resp: Response) -> bool:
    try:
        return bool(target.check(resp))
    except Exception:
        return False


def run_probe(
    targets: list[ProbeTarget],
    fetch: Fetcher,
    pause_s: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    for i, t in enumerate(targets):
        if i > 0:
            sleep(pause_s)
        try:
            resp = fetch(t.url)
        except Exception as e:  # eine Quelle darf den Lauf nie abbrechen
            results.append(ProbeResult(t.key, t.name, t.url, False, None, None, None, f"{type(e).__name__}: {e}", t.purpose))
            continue
        if resp.status != 200:
            ok, error = False, f"HTTP {resp.status}"
        elif not _passes(t, resp):
            ok, error = False, "Inhalt unerwartet"
        else:
            ok, error = True, None
        results.append(
            ProbeResult(t.key, t.name, t.url, ok, resp.status, resp.elapsed_ms, len(resp.text.encode("utf-8")), error, t.purpose)
        )
    return results

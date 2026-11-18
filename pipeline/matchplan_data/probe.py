"""Quellen-Check: prüft, ob jede geplante Datenquelle erreichbar ist und echte Daten liefert."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
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
    sample: str | None = None  # Anfang der Antwort, nur bei Fehlern


def decode_body(content: bytes, encoding: str | None) -> str:
    """UTF-8-BOM gewinnt immer; sonst die angegebene Kodierung, ohne Angabe UTF-8."""
    if content.startswith(b"\xef\xbb\xbf"):
        return content[3:].decode("utf-8", errors="replace")
    return content.decode(encoding or "utf-8", errors="replace")


def http_fetch(url: str) -> Response:
    started = time.monotonic()
    r = requests.get(
        url,
        timeout=TIMEOUT_S,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"},
    )
    ctype = r.headers.get("Content-Type", "")
    text = "" if ctype.startswith("image/") else decode_body(r.content, r.encoding)
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
            ProbeResult(t.key, t.name, t.url, ok, resp.status, resp.elapsed_ms, len(resp.text.encode("utf-8")), error,
                        t.purpose, None if ok else " ".join(resp.text.split())[:200])
        )
    return results


def _json_list_nonempty(r: Response) -> bool:
    data = json.loads(r.text)
    return isinstance(data, list) and len(data) >= 1


TARGETS: list[ProbeTarget] = [
    ProbeTarget("openligadb", "OpenLigaDB", "https://api.openligadb.de/getmatchdata/bl1/2026",
                _json_list_nonempty, "Spielplan, Ergebnisse, Tabelle"),
    ProbeTarget("fotmob_web", "FotMob (Webseite)", "https://www.fotmob.com/leagues/54/overview/bundesliga",
                lambda r: "__NEXT_DATA__" in r.text, "Spielstatistik, Noten, Kader"),
    ProbeTarget("understat", "Understat", "https://understat.com/league/Bundesliga/2026",
                lambda r: "teamsData" in r.text, "xG pro Schuss, Schusskarten"),
    ProbeTarget("bundesliga", "bundesliga.com", "https://www.bundesliga.com/en/bundesliga/stats/players",
                lambda r: "Distance covered" in r.text or "distance" in r.text, "Laufdaten, Match Facts"),
    ProbeTarget("ligainsider", "Ligainsider", "https://www.ligainsider.de/borussia-moenchengladbach/5/",
                lambda r: r.text.count("player_position_row") >= 4, "Voraussichtliche Aufstellungen, Ausfälle"),
    ProbeTarget("ligainsider_img", "Ligainsider (Bilder)",
                "https://cdn.ligainsider.de/images/teams/small/fc-bayern-muenchen-wappen.png",
                lambda r: r.content_type.startswith("image/"), "Spielerfotos, Wappen"),
    ProbeTarget("transfermarkt", "Transfermarkt", "https://www.transfermarkt.de/bundesliga/startseite/wettbewerb/L1",
                lambda r: "Bundesliga" in r.text and "captcha" not in r.text.lower(), "Karrieren, Marktwerte"),
    ProbeTarget("clubelo", "ClubElo", "http://api.clubelo.com/Bayern",
                lambda r: r.text.startswith("Rank,Club"), "Elo-Stärke der Teams"),
    ProbeTarget("footballdata", "football-data.co.uk", "https://www.football-data.co.uk/mmz4281/2627/D1.csv",
                lambda r: r.text.startswith("Div,"), "Quoten, historische Ergebnisse"),
]


def build_report(results: list[ProbeResult], now: datetime) -> dict:
    return {
        "checked_at": now.isoformat(),
        "ok_count": sum(1 for r in results if r.ok),
        "total": len(results),
        "sources": [asdict(r) for r in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prüft alle Datenquellen und schreibt einen Bericht.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    results = run_probe(TARGETS, lambda u: http_fetch(u), sleep=lambda s: time.sleep(s))
    report = build_report(results, datetime.now(timezone.utc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for r in results:
        print(f"{'OK  ' if r.ok else 'FAIL'} {r.name:24} {r.status or '-':>4} {r.error or ''}")
    print(f"{report['ok_count']} von {report['total']} Quellen erreichbar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

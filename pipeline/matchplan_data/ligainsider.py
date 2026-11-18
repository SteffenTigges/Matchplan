"""Ligainsider: voraussichtliche Aufstellung, Alternativen, Ausfälle und Spielerfotos einer Vereinsseite."""

from __future__ import annotations

import html as H
import re
from dataclasses import dataclass, field


@dataclass
class Player:
    id: str
    name: str
    photo: str | None


@dataclass
class Slot:
    player: Player
    alternatives: list[Player] = field(default_factory=list)


@dataclass
class TeamLineup:
    team: str
    formation: str
    rows: list[list[Slot]]
    missing: list[dict]
    updated_label: str | None
    opponent: str | None
    home: bool | None


_TITLE = re.compile(r"<title>\s*([^<:]+?)\s*:\s*Voraussichtliche Aufstellung", re.I)
_PLAYER = re.compile(
    r'<img class="img-circle" src="([^"]+)"[^>]*>.*?'
    r'class="player_name"><a href="https://www\.ligainsider\.de/([^/"]+)/"[^>]*>([^<]+)</a>',
    re.S,
)
_NAME_ONLY = re.compile(r'class="player_name"><a href="https://www\.ligainsider\.de/([^/"]+)/"[^>]*>([^<]+)</a>')


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", H.unescape(s).replace("­", "")).strip()


def _players(column_html: str) -> list[Player]:
    """Eine Spalte enthält den Starter und ggf. Alternativen, jeweils als eigener Block."""
    blocks = column_html.split('class="sub_child"')[1:] or [column_html]
    out = []
    for b in blocks:
        m = _PLAYER.search(b)
        if m:
            out.append(Player(m.group(2), _clean(m.group(3)), m.group(1)))
            continue
        n = _NAME_ONLY.search(b)
        if n:
            out.append(Player(n.group(1), _clean(n.group(2)), None))
    return out


def _missing(page: str, start: int) -> list[dict]:
    i = page.find("fehlen</h3>", start)
    if i < 0:
        return []
    end = page.find("Ergebnisse und n", i)
    block = page[i : end if end > 0 else i + 40000]
    out = []
    for row in block.split('class="small_table_row"')[1:]:
        name = re.search(r'left_title"><strong><a[^>]*>([^<]+)</a>', row)
        if not name:
            continue
        kind = re.search(r'alt="([^"]+)"', row)
        spans = [_clean(re.sub(r"<[^>]+>", "", s)).strip('"') for s in re.findall(r"<span>(.*?)</span>", row, re.S)]
        spans = [s for s in spans if s]
        out.append({"name": _clean(name.group(1)), "kind": kind.group(1) if kind else "", "note": spans[0] if spans else ""})
    return out


def parse_lineup_page(page: str) -> TeamLineup | None:
    title = _TITLE.search(page)
    start = page.find("VORAUSSICHTLICHE AUFSTELLUNG")
    if not title or start < 0:
        return None
    end = page.find("Letzte Aktualisierung", start)
    seg = page[start : end if end > 0 else len(page)]

    rows: list[list[Slot]] = []
    for r in seg.split('class="player_position_row')[1:]:
        row = []
        for col in r.split('class="player_position_column')[1:]:
            ps = _players(col)
            if ps:
                row.append(Slot(ps[0], ps[1:]))
        if row:
            rows.append(row)
    if sum(len(r) for r in rows) != 11:
        return None

    head = _clean(re.sub(r"<[^>]+>", " ", seg[:8000]))
    m = re.search(r"(Heimspiel|Auswärtsspiel)\s+.+?\s+gegen\s+(.+?)\s+(?:\[|\d+,\s*\d|VORSCHAU|$)", head)
    upd = re.search(r"Letzte Aktualisierung:\s*([^<]+)", page[end : end + 300]) if end > 0 else None
    return TeamLineup(
        team=_clean(title.group(1)),
        formation="-".join(str(len(r)) for r in rows[1:]),
        rows=rows,
        missing=_missing(page, end if end > 0 else start),
        updated_label=_clean(upd.group(1)) if upd else None,
        opponent=_clean(m.group(2)) if m else None,
        home=(m.group(1) == "Heimspiel") if m else None,
    )


def diagnose(page: str) -> str:
    """Kurze Begründung, warum parse_lineup_page() nichts findet ('ok', wenn alles passt)."""
    title = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    title_text = _clean(title.group(1))[:80] if title else "(kein Titel)"
    if not _TITLE.search(page):
        return f"Titel ohne 'Voraussichtliche Aufstellung': {title_text} · {len(page)} Zeichen"
    start = page.find("VORAUSSICHTLICHE AUFSTELLUNG")
    if start < 0:
        return f"Abschnitt 'VORAUSSICHTLICHE AUFSTELLUNG' fehlt · {len(page)} Zeichen"
    end = page.find("Letzte Aktualisierung", start)
    seg = page[start : end if end > 0 else len(page)]
    rows = [r for r in seg.split('class="player_position_row')[1:]]
    cols = [c for r in rows for c in r.split('class="player_position_column')[1:]]
    starters = sum(1 for c in cols if _players(c))
    if starters != 11:
        return (f"{starters} Spieler statt 11 · {len(rows)} Reihen · {len(cols)} Spalten · "
                f"{seg.count('sub_child')} sub_child · {seg.count('player_name')} Namen")
    return "ok"

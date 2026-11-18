"""Verlauf der Woche: vergleicht zwei Ligainsider-Stände eines Teams und erzeugt Änderungs-Ereignisse."""

from __future__ import annotations

import json
from pathlib import Path

from .ligainsider import Slot, TeamLineup


def _slots(lu: TeamLineup) -> list[Slot]:
    return [s for row in lu.rows for s in row]


def diff_lineups(team_key: str, old: TeamLineup | None, new: TeamLineup, at: str) -> list[dict]:
    def ev(kind: str, text: str) -> dict:
        return {"at": at, "team": team_key, "kind": kind, "text": text}

    if old is None:
        return [ev("first", f"Erste Prognose: {new.formation}")]

    events: list[dict] = []
    if old.formation != new.formation:
        events.append(ev("formation", f"Formation {old.formation} → {new.formation}"))

    old_ids = {s.player.id for s in _slots(old)}
    new_ids = {s.player.id for s in _slots(new)}
    events += [ev("in", f"{s.player.name} rückt in die Startelf") for s in _slots(new) if s.player.id not in old_ids]
    events += [ev("out", f"{s.player.name} nicht mehr in der Startelf") for s in _slots(old) if s.player.id not in new_ids]

    old_alts = {s.player.id: s.alternatives for s in _slots(old)}
    for s in _slots(new):
        if s.alternatives and s.player.id in old_alts and not old_alts[s.player.id]:
            events.append(ev("alt", f"Offen: {s.player.name} oder {'/'.join(a.name for a in s.alternatives)}"))

    old_missing = {m["name"] for m in old.missing}
    new_missing = {m["name"] for m in new.missing}
    events += [ev("missing", f"Fällt aus: {m['name']} ({m['kind']})") for m in new.missing if m["name"] not in old_missing]
    events += [ev("back", f"Wieder dabei: {m['name']}") for m in old.missing if m["name"] not in new_missing]
    return events


def append_history(directory: Path, matchday: int, events: list[dict]) -> None:
    path = Path(directory) / f"history-{matchday}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"matchday": matchday, "events": []}
    data["events"].extend(events)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

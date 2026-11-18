import json

from matchplan_data.history import append_history, diff_lineups
from matchplan_data.ligainsider import Player, Slot, TeamLineup

AT = "2026-11-18T16:00:00+00:00"


def lineup(starters, formation="4-4-2", missing=(), alts=None):
    alts = alts or {}
    slots = [Slot(Player(n.lower(), n, None), [Player(a.lower(), a, None) for a in alts.get(n, [])]) for n in starters]
    return TeamLineup("X", formation, [slots[:1], slots[1:]], list(missing), None, None, True)


ELF = ["Nicolas", "Diks", "Sander", "Chiarodia", "Scally", "Uno", "Neuhaus", "Herold", "Hack", "Machino", "Mohya"]


def test_first_snapshot_yields_first_event():
    ev = diff_lineups("BMG", None, lineup(ELF, "3-4-3"), AT)
    assert ev == [{"at": AT, "team": "BMG", "kind": "first", "text": "Erste Prognose: 3-4-3"}]


def test_identical_snapshots_produce_no_events():
    assert diff_lineups("BMG", lineup(ELF), lineup(ELF), AT) == []


def test_player_swap_yields_in_and_out():
    new = [*ELF[:7], "Castrop", *ELF[8:]]
    texts = [e["text"] for e in diff_lineups("BMG", lineup(ELF), lineup(new), AT)]
    assert texts == ["Castrop rückt in die Startelf", "Herold nicht mehr in der Startelf"]


def test_formation_change():
    ev = diff_lineups("BMG", lineup(ELF, "4-4-2"), lineup(ELF, "3-5-2"), AT)
    assert [e["text"] for e in ev] == ["Formation 4-4-2 → 3-5-2"]


def test_new_alternative_is_reported():
    ev = diff_lineups("BMG", lineup(ELF), lineup(ELF, alts={"Machino": ["Lidberg", "Kleindienst"]}), AT)
    assert [e["text"] for e in ev] == ["Offen: Machino oder Lidberg/Kleindienst"]


def test_new_absence_and_return():
    old = lineup(ELF, missing=[{"name": "Itakura", "kind": "Sperre", "note": ""}])
    new = lineup(ELF, missing=[{"name": "Ullrich", "kind": "Verletzung", "note": "Schlüsselbeinbruch"}])
    assert [e["text"] for e in diff_lineups("BMG", old, new, AT)] == ["Fällt aus: Ullrich (Verletzung)", "Wieder dabei: Itakura"]


def test_history_is_per_matchday(tmp_path):
    e1 = [{"at": AT, "team": "BMG", "kind": "first", "text": "a"}]
    e2 = [{"at": AT, "team": "BMG", "kind": "first", "text": "b"}]
    append_history(tmp_path, 10, e1)
    append_history(tmp_path, 10, e2)
    append_history(tmp_path, 11, e1)
    md10 = json.loads((tmp_path / "history-10.json").read_text(encoding="utf-8"))
    assert md10["matchday"] == 10 and [e["text"] for e in md10["events"]] == ["a", "b"]
    assert len(json.loads((tmp_path / "history-11.json").read_text(encoding="utf-8"))["events"]) == 1

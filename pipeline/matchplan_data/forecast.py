"""Datenjob-Schritt Prognose: Kalibrierung, Quoten, Prognosen des aktuellen Spieltags, Modellprüfung."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from .elo import game_rows, rank as elo_rank, run_elo, win_draw_loss
from .odds import FIXTURES_URL, closing_odds, odds_by_pair, parse_csv, results, season_url
from .predict import (DEFAULT_CAL, Means, TeamGame, expected_goals, markets, outcome_probs, score_matrix,
                      season_means, strengths, tip)
from .scorers import absence_factors, match_player, player_season, scorers
from .teams import FD_NAMES, TEAMS

SEASON = 2026
CAL_FRESH = timedelta(days=7)
CAL_SEASONS = 3


def _read(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _r(x: float, n: int = 4) -> float:
    return round(x, n)


def _calibration(out: Path, get: Callable[[str], str], now: datetime, at: str) -> tuple[dict, str | None]:
    old = (_read(out / "model.json") or {}).get("calibration")
    if old and old.get("fetched_at") and now - datetime.fromisoformat(old["fetched_at"]) < CAL_FRESH:
        return old, None
    try:
        res = []
        for y in range(SEASON - CAL_SEASONS, SEASON):
            res += results(parse_csv(get(season_url(y))))
        if len(res) < 300:
            raise RuntimeError(f"nur {len(res)} Spiele")
        from .predict import fit_calibration
        return {**fit_calibration(res), "matches": len(res), "seasons": f"{SEASON - CAL_SEASONS}–{SEASON - 1}", "fetched_at": at}, None
    except Exception as e:
        return (old or {**DEFAULT_CAL, "matches": 0, "seasons": None, "fetched_at": None}), f"Kalibrierung: {e}"


ELO_FROM = 2016


def _elo(out: Path, get: Callable[[str], str], cur_rows: list[dict], now: datetime, at: str) -> tuple[dict, dict | None, str | None]:
    """Elo je Team: Stand nach der Vorsaison (wöchentlich neu aus 1. und 2. Liga seit 2016) plus laufende Saison."""
    old = (_read(out / "model.json") or {}).get("elo_base")
    err = None
    if not (old and old.get("fetched_at") and now - datetime.fromisoformat(old["fetched_at"]) < CAL_FRESH):
        try:
            rows = []
            for y in range(ELO_FROM, SEASON):
                for div in ("D1", "D2"):
                    rows += parse_csv(get(season_url(y).replace("/D1.csv", f"/{div}.csv")))
            games = game_rows(rows)
            if len(games) < 1000:
                raise RuntimeError(f"nur {len(games)} Spiele")
            old = {"ratings": {k: round(v, 1) for k, v in run_elo(games).items()}, "games": len(games), "fetched_at": at}
        except Exception as e:
            err = f"Elo: {e}"
    if not old:
        return {}, None, err
    cur = run_elo(game_rows([r for r in cur_rows if r.get("Div") == "D1"]), base=old["ratings"])
    ours = {FD_NAMES[n]: v for n, v in cur.items() if n in FD_NAMES}
    rk = elo_rank(ours)
    return {k: {"elo": round(v), "rank": rk[k]} for k, v in ours.items()}, old, err


def _games(out: Path, matchdays: dict[int, list[dict]]) -> tuple[list[TeamGame], list[dict]]:
    files = []
    games: list[TeamGame] = []
    for md, ms in matchdays.items():
        for m in ms:
            if not m.get("finished") or not m.get("score"):
                continue
            fm = _read(out / "fotmob" / f"{m['id']}.json") or {}
            if fm:
                files.append(fm)
            xg = (fm.get("stats") or {}).get("expected_goals")
            hg, ag = m["score"]
            xh, xa = (float(xg[0]), float(xg[1])) if xg and None not in xg[:2] else (float(hg), float(ag))
            games.append(TeamGame(md, m["home"], m["away"], True, xh, xa, hg, ag))
            games.append(TeamGame(md, m["away"], m["home"], False, xa, xh, ag, hg))
    return games, files


def _form(matchdays: dict[int, list[dict]], team: str, before: int) -> float | None:
    pts = []
    for md in sorted(matchdays):
        if md >= before:
            break
        for m in matchdays[md]:
            if m.get("finished") and m.get("score") and team in (m["home"], m["away"]):
                h, a = m["score"]
                mine, theirs = (h, a) if m["home"] == team else (a, h)
                pts.append(3 if mine > theirs else 1 if mine == theirs else 0)
    last = pts[-5:]
    return round(sum(last) / len(last), 2) if last else None


def _predict(home: str, away: str, games: list[TeamGame], cal: dict, played: int, abs_h=(1.0, 1.0), abs_a=(1.0, 1.0)):
    keys = [t.key for t in TEAMS]
    st = strengths(games, keys)
    means = season_means(games, cal, played)
    lh, la = expected_goals(home, away, st, means)
    lh, la = lh * abs_h[0] * abs_a[1], la * abs_a[0] * abs_h[1]
    m = score_matrix(lh, la, cal["rho"])
    return m, lh, la, st, means


def _xi(lineup: dict | None) -> list[dict]:
    return [{"li_id": s["player"].get("id"), "name": s["player"].get("name")} for row in (lineup or {}).get("rows") or [] for s in row]


def _hits(xi: list[dict], fm_players: list[dict]) -> int | None:
    if not xi or not fm_players:
        return None
    return sum(1 for p in xi if match_player({"id": p.get("li_id"), "name": p.get("name")}, fm_players))


def run_forecast(out: Path, get: Callable[[str], str], matchdays: dict[int, list[dict]], current: int,
                 lineups: dict[str, dict], now: datetime, at: str, status: dict) -> None:
    out = Path(out)
    cal, cal_err = _calibration(out, get, now, at)

    odds, odds_err, unknown = {}, None, []
    try:
        odds, unknown = odds_by_pair(parse_csv(get(FIXTURES_URL)))
    except Exception as e:
        odds_err = str(e)
    closing: dict = {}
    cur_rows: list[dict] = []
    try:
        cur_rows = parse_csv(get(season_url(SEASON)))
        closing, more = closing_odds(cur_rows)
        unknown += [u for u in more if u not in unknown]
    except Exception:
        pass
    status["quoten"] = {"ok": odds_err is None, "at": at, "error": odds_err,
                        "note": f"{len(odds)} Spiele mit Quoten" + (f"; unbekannte Namen: {', '.join(unknown)}" if unknown else "")}

    elo, elo_base, elo_err = _elo(out, get, cur_rows, now, at)
    games, files = _games(out, matchdays)
    season_players = player_season(files, SEASON)
    index = _read(out / "players.json") or {}
    pos = {p["id"]: p.get("pos") for p in index.get("players", [])}
    played = max((g.matchday for g in games), default=0)

    # --- Prognosen des aktuellen Spieltags (angepfiffene bleiben eingefroren) ---
    path = out / "predictions" / f"{current}.json"
    stored = (_read(path) or {}).get("matches", {})
    preds: dict[str, dict] = dict(stored)
    made = 0
    for m in matchdays.get(current, []):
        mid = str(m["id"])
        kick = datetime.fromisoformat(m["kickoff"].replace("Z", "+00:00")) if m.get("kickoff") else None
        if m.get("finished") or (kick and kick <= now):
            continue
        h, a = m["home"], m["away"]
        lu_h, lu_a = lineups.get(h), lineups.get(a)
        ah = absence_factors((lu_h or {}).get("missing") or [], season_players.get(h, []))
        aa = absence_factors((lu_a or {}).get("missing") or [], season_players.get(a, []))
        mat, lh, la, st, means = _predict(h, a, games, cal, played, ah[:2], aa[:2])
        ph, pd, pa = outcome_probs(mat)
        sc = {side: [{k: (_r(v) if isinstance(v, float) else v) for k, v in e.items()}
                     for e in scorers(lu, season_players.get(team, []), st[team]["xgf"], lam, pos)] if lu else []
              for side, team, lu, lam in (("home", h, lu_h, lh), ("away", a, lu_a, la))}
        preds[mid] = {
            "home": h, "away": a, "kickoff": m.get("kickoff"), "made_at": at,
            "xg": [_r(lh, 2), _r(la, 2)], "probs": [_r(ph), _r(pd), _r(pa)], "tip": list(tip(mat)),
            "tip_prob": _r(mat[tip(mat)[0]][tip(mat)[1]]),
            "matrix": [[_r(mat[i][j]) for j in range(6)] for i in range(6)],
            "markets": {k: _r(v) for k, v in markets(mat).items()},
            "odds": ({k: (_r(v) if isinstance(v, float) else v) for k, v in odds[(h, a)].items()} if (h, a) in odds else None),
            "scorers": sc,
            "elo": ({"home": elo[h]["elo"], "away": elo[a]["elo"], "probs": [_r(x) for x in win_draw_loss(elo[h]["elo"], elo[a]["elo"])]}
                    if h in elo and a in elo else None),
            "xi": {"home": _xi(lu_h), "away": _xi(lu_a)},
            "why": {
                "attack": [_r(st[h]["att"], 3), _r(st[a]["att"], 3)],
                "defence": [_r(st[h]["def"], 3), _r(st[a]["def"], 3)],
                "xgf": [_r(st[h]["xgf"], 2), _r(st[a]["xgf"], 2)], "xga": [_r(st[h]["xga"], 2), _r(st[a]["xga"], 2)],
                "n": [st[h]["n"], st[a]["n"]],
                "form": [_form(matchdays, h, current), _form(matchdays, a, current)],
                "means": [_r(means.home, 3), _r(means.away, 3)], "rho": cal["rho"],
                "absence_factor": [[ah[0], ah[1]], [aa[0], aa[1]]],
                "absences": {"home": ah[2], "away": aa[2]},
            },
        }
        made += 1
    if preds:
        _write(path, {"matchday": current, "season": SEASON, "updated_at": at, "matches": preds})

    # --- Abgleich voraussichtliche ↔ tatsächliche Startelf ---
    for md in (current - 1, current):
        p = out / "predictions" / f"{md}.json"
        data = _read(p)
        if not data:
            continue
        changed = False
        for mid, e in data.get("matches", {}).items():
            fm = _read(out / "fotmob" / f"{mid}.json") or {}
            lu = fm.get("lineups") or {}
            if not e.get("xi") or not lu or "lineup_hits" in e:
                continue
            e["lineup_hits"] = {side: _hits(e["xi"].get(side) or [], (lu.get(side) or {}).get("players") or []) for side in ("home", "away")}
            changed = True
        if changed:
            _write(p, data)

    # --- Modellprüfung: jedes beendete Spiel nur mit früheren Spieltagen vorhergesagt ---
    check = []
    for md in sorted(matchdays):
        before = [g for g in games if g.matchday < md]
        prior = max((g.matchday for g in before), default=0)
        for m in matchdays[md]:
            if not m.get("finished") or not m.get("score"):
                continue
            mat, *_ = _predict(m["home"], m["away"], before, cal, prior)
            probs = outcome_probs(mat)
            hg, ag = m["score"]
            res = 0 if hg > ag else 1 if hg == ag else 2
            t = tip(mat)
            o = closing.get((m["home"], m["away"]))
            entry = {"id": m["id"], "md": md, "probs": [_r(x) for x in probs], "tip": list(t), "score": [hg, ag],
                     "tendency": (0 if t[0] > t[1] else 1 if t[0] == t[1] else 2) == res, "exact": list(t) == [hg, ag],
                     "brier": _r(sum((p - (i == res)) ** 2 for i, p in enumerate(probs)))}
            if o:
                entry["brier_odds"] = _r(sum((p - (i == res)) ** 2 for i, p in enumerate((o["home"], o["draw"], o["away"]))))
            check.append(entry)
    n = len(check)
    with_odds = [c for c in check if "brier_odds" in c]
    by_md = []
    for md in sorted({c["md"] for c in check}):
        cs = [c for c in check if c["md"] == md]
        by_md.append({"md": md, "matches": len(cs), "tendency": sum(c["tendency"] for c in cs), "exact": sum(c["exact"] for c in cs),
                      "brier": _r(sum(c["brier"] for c in cs) / len(cs))})
    _write(out / "model.json", {
        "updated_at": at, "calibration": cal, "elo": elo, "elo_base": elo_base,
        "check": {"matches": n,
                  "tendency_rate": _r(sum(c["tendency"] for c in check) / n) if n else None,
                  "exact_rate": _r(sum(c["exact"] for c in check) / n) if n else None,
                  "brier": _r(sum(c["brier"] for c in check) / n) if n else None,
                  "odds_matches": len(with_odds),
                  "brier_model_same": _r(sum(c["brier"] for c in with_odds) / len(with_odds)) if with_odds else None,
                  "brier_odds": _r(sum(c["brier_odds"] for c in with_odds) / len(with_odds)) if with_odds else None,
                  "by_matchday": by_md, "games": check},
    })
    status["prognose"] = {"ok": True, "at": at, "error": "; ".join(x for x in (cal_err, elo_err) if x) or None,
                          "note": f"{made} Spiele vorhergesagt, Modellprüfung über {n} Spiele"}

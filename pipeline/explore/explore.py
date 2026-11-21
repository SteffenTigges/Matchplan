import json, subprocess, sys
sys.path.insert(0, ".")
from matchplan_data.probe import http_fetch
from matchplan_data.fotmob import next_data

print(subprocess.run(["curl", "-s", "-D", "-", "-o", "/dev/null", "-H", "Origin: https://steffentigges.github.io",
                      "https://api.openligadb.de/getmatchdata/bl1/2026/10"], capture_output=True, text=True).stdout)
nd = next_data(http_fetch("https://www.fotmob.com/match/5881226").text)
pp = nd["props"]["pageProps"]
print("header", json.dumps(pp.get("header"), ensure_ascii=False)[:1500])
mf = pp["content"]["matchFacts"]
print("matchFacts keys", list(mf))
ev = mf.get("events") or {}
print("events keys", list(ev) if isinstance(ev, dict) else type(ev))
evs = ev.get("events") if isinstance(ev, dict) else ev
for e in (evs or [])[:40]:
    print(json.dumps({k: e.get(k) for k in ("type", "time", "overloadTime", "timeStr", "isHome", "player", "nameStr", "card", "swap", "newScore", "isPenaltyShootoutEvent", "ownGoal", "assistStr", "minutesAddedStr", "halfStrShort", "shotmapEvent", "goalDescription", "eventId")}, ensure_ascii=False)[:400])
print("general", json.dumps(pp.get("general"), ensure_ascii=False)[:800])

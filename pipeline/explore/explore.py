import json, sys
sys.path.insert(0, ".")
from matchplan_data.probe import http_fetch
from matchplan_data.fotmob import next_data


def get(u):
    r = http_fetch(u)
    print(f"\n=== {u} -> {r.status} {len(r.text)}")
    return r.text if r.status == 200 else None


nd = next_data(get("https://www.fotmob.com/match/5881219"))
c = nd["props"]["pageProps"]["content"]
for g in c["stats"]["Periods"]["All"]["stats"]:
    print("GROUP", g.get("title"), [(s.get("key"), s.get("stats")) for s in g.get("stats") or []])
ps = next(iter(c["playerStats"].values()))
print("PLAYER", ps.get("name"), [s.get("key") for g in ps.get("stats") or [] for s in (g.get("stats") or {}).values()])
lg = next_data(get("https://www.fotmob.com/leagues/54/stats/bundesliga"))
for x in lg["props"]["pageProps"]["stats"].get("teams", []):
    if any(k in x["fetchAllUrl"] for k in ("poss_won_att_3rd", "interception_team", "total_tackle_team")):
        t = json.loads(get(x["fetchAllUrl"]))
        tl = t["TopLists"][0]
        print("  ", tl.get("Title"), tl.get("Subtitle"), json.dumps(tl["StatList"][:3], ensure_ascii=False)[:700])

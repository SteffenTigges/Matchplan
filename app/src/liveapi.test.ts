import { expect, test } from "vitest";
import type { Match } from "./data";
import { mergeOldb } from "./liveapi";
import { approxMinute, isLive } from "./views/live";

const m: Match = { id: 1, kickoff: "2026-11-21T14:30:00Z", home: "BMG", away: "BVB", finished: false, score: null, halftime: null, goals: [] };

test("merge_oldb_live_goals_in_order", () => {
  const out = mergeOldb([m], [{ matchID: 1, matchIsFinished: false, matchResults: [],
    goals: [{ matchMinute: 55, scoreTeam1: 1, scoreTeam2: 1, goalGetterName: "Adeyemi", isPenalty: false, isOwnGoal: false },
            { matchMinute: 12, scoreTeam1: 1, scoreTeam2: 0, goalGetterName: "Kleindienst", isPenalty: true, isOwnGoal: false }] }]);
  expect(out[0]!.score).toEqual([1, 1]);
  expect(out[0]!.goals.map((g) => [g.minute, g.team, g.scorer])).toEqual([[12, "BMG", "Kleindienst"], [55, "BVB", "Adeyemi"]]);
  expect(out[0]!.goals[0]!.penalty).toBe(true);
  expect(out[0]!.finished).toBe(false);
});

test("live_window_and_minute", () => {
  expect(isLive(m, new Date("2026-11-21T15:00:00Z"))).toBe(true);
  expect(isLive(m, new Date("2026-11-21T14:00:00Z"))).toBe(false);
  expect(isLive({ ...m, finished: true }, new Date("2026-11-21T15:00:00Z"))).toBe(false);
  expect(approxMinute(m.kickoff!, new Date("2026-11-21T14:50:00Z"))).toBe("~20'");
  expect(approxMinute(m.kickoff!, new Date("2026-11-21T15:20:00Z"))).toBe("Halbzeit");
  expect(approxMinute(m.kickoff!, new Date("2026-11-21T15:40:00Z"))).toBe("~55'");
});

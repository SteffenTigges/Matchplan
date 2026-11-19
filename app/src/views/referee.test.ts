import { expect, test } from "vitest";
import type { Referees, Season } from "../data";
import { renderReferee } from "./referee";

const season: Season = { season: 2026, current_matchday: 10, updated_at: "", teams: { FCB: { name: "FC Bayern", short: "Bayern", color: "#d00", crest: "" } } };
const refs: Referees = {
  updated_at: "", league: { yellow_pg: 3.9, fouls_pg: 22.1, penalties_pg: 0.25 },
  referees: { "Felix Zwayer": { name: "Felix Zwayer", id: 1, games: 5, yellow_pg: 4.6, red: 1, fouls_pg: 24.2, penalties: 2, penalties_pg: 0.4, home_win: 0.6, draw: 0.2, away_win: 0.2, teams: { FCB: { games: 2, points: 6 } } } },
  upcoming: { "83237": { name: "Felix Zwayer", id: 1 }, "83238": { name: "Neuer Schiri", id: 2 } },
};

test("shows_referee_with_league_average", () => {
  const html = renderReferee(83237, refs, season, ["FCB"]);
  expect(html).toContain("Felix Zwayer");
  expect(html).toContain("4,60");
  expect(html).toContain("Ø 3,90");
  expect(html).toContain("Bayern unter ihm");
});

test("not_yet_assigned_and_new_referee", () => {
  expect(renderReferee(1, refs, season)).toContain("Noch nicht angesetzt");
  expect(renderReferee(83238, refs, season)).toContain("erstes Bundesliga-Spiel");
});

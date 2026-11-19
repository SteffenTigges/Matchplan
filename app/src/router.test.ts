import { expect, test } from "vitest";
import { parseRoute } from "./router";

test("parses_all_routes", () => {
  expect(parseRoute("")).toEqual({ view: "spiele" });
  expect(parseRoute("#unbekannt")).toEqual({ view: "spiele" });
  expect(parseRoute("#spiele")).toEqual({ view: "spiele" });
  expect(parseRoute("#spiele/12")).toEqual({ view: "spiele", matchday: 12 });
  expect(parseRoute("#spiel/83228")).toEqual({ view: "spiel", id: 83228 });
  expect(parseRoute("#teams")).toEqual({ view: "teams" });
  expect(parseRoute("#team/BMG")).toEqual({ view: "team", key: "BMG" });
  expect(parseRoute("#status")).toEqual({ view: "status" });
});

test("rejects_invalid_numbers", () => {
  expect(parseRoute("#spiele/99")).toEqual({ view: "spiele" });
  expect(parseRoute("#spiel/abc")).toEqual({ view: "spiele" });
});

test("parses_player_routes", () => {
  expect(parseRoute("#spieler")).toEqual({ view: "spieler" });
  expect(parseRoute("#spieler/1219540")).toEqual({ view: "spieler", id: 1219540 });
  expect(parseRoute("#spieler/abc")).toEqual({ view: "spieler" });
});

test("parses_rank_route", () => {
  expect(parseRoute("#rang/xg_pg/TSG")).toEqual({ view: "rang", metric: "xg_pg", key: "TSG" });
  expect(parseRoute("#rang/<x>/TSG")).toEqual({ view: "spiele" });
});

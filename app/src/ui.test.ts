import { expect, test } from "vitest";
import { berlin, crest, photo } from "./ui";

const bmg = { short: "Gladbach", color: "#1b1b1b", crest: "https://cdn.ligainsider.de/x.png" };

test("berlin_formats_weekday_date_time", () => {
  expect(berlin("2026-11-21T14:30:00Z")).toBe("Sa. 21.11., 15:30");
});

test("crest_falls_back_on_error", () => {
  const html = crest(bmg, 28);
  expect(html).toContain('src="https://cdn.ligainsider.de/x.png"');
  expect(html).toContain("onerror");
});

test("photo_has_fallback_handler", () => {
  const html = photo("https://cdn.ligainsider.de/p.jpg", "Herold", 40);
  expect(html).toContain("onerror");
  expect(html).toContain('alt="Herold"');
});

test("photo_without_url_shows_initials", () => {
  expect(photo(null, "Jens Castrop", 40)).toContain(">JC<");
});

test("crest_carries_team_key_for_navigation", () => {
  expect(crest({ short: "Bayern", color: "#d00", crest: "fcb.png", key: "FCB" })).toContain('data-team="FCB"');
  const fallback = crest({ short: "Bayern", color: "#d00", key: "FCB" });
  expect(fallback).toContain('data-team="FCB"');
  expect(crest({ short: "X", color: "#000", crest: "x.png" })).not.toContain("data-team");
});

test("find_player_by_full_short_and_abbreviated_name", async () => {
  const { findPlayer } = await import("./ui");
  const links = { names: { FCB: { "harry kane": 2, "luis diaz": 3 }, BVB: { "felix nmecha": 9, "lukas nmecha": 10 } } };
  expect(findPlayer(links, "Harry Kane", "FCB")).toBe(2);
  expect(findPlayer(links, "Díaz", "FCB")).toBe(3);
  expect(findPlayer(links, "F. Nmecha", "BVB")).toBe(9);
  expect(findPlayer(links, "Nmecha", "BVB")).toBeNull();
  expect(findPlayer(links, "Kane", "BVB")).toBe(2);
  expect(findPlayer(null, "Kane")).toBeNull();
});

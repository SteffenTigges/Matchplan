import { expect, test } from "vitest";
import { legendFor } from "./legend";

test("legend_lists_formation_when_present", () => {
  const html = legendFor('<span class="chip">Gladbach · 3-4-3</span>');
  expect(html).toContain("3-4-3");
  expect(html).toContain("Abwehr, Mittelfeld");
});

test("legend_lists_alternative_marker", () => {
  expect(legendFor("<text>oder Castrop</text>")).toContain("oder …");
});

test("legend_empty_when_no_terms", () => {
  expect(legendFor("<p>Bayern gegen Köln</p>")).toBe("");
});

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

test("legend_explains_xg_when_present", () => {
  const html = legendFor("<span>xG pro Spiel</span><span>PPDA</span><span>Field Tilt</span>");
  expect(html).toContain("Expected Goals");
  expect(html).toContain("PPDA");
  expect(html).toContain("Field Tilt");
});

test("legend_skips_absent_terms", () => {
  const html = legendFor("<span>xG</span>");
  expect(html).not.toContain("PPDA");
  expect(html).not.toContain("xGOT");
});

test("legend_explains_percentile_and_per90", () => {
  const html = legendFor('<p>Perzentil pro 90 Minuten</p><span class="pp">0,55 /90</span>');
  expect(html).toContain("Perzentil");
  expect(html).toContain("/90");
});

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

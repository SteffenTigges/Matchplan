import { esc } from "./ui";

// Nur Fachbegriffe und Abkürzungen; Grundbegriffe (Sieg/Remis, Formkurve usw.) werden bewusst nicht erklärt.
const GLOSSAR: { test: RegExp; term: (m: RegExpMatchArray) => string; text: string }[] = [
  { test: /\b\d-\d-\d(?:-\d)?\b/, term: (m) => m[0], text: "Grundordnung: Zahl der Spieler in Abwehr, Mittelfeld und Angriff, ohne Torwart." },
  { test: /oder [A-ZÄÖÜ]/, term: () => "oder …", text: "Ligainsider hält diese Position für offen und nennt die Alternative." },
];

export function legendFor(html: string): string {
  const text = html.replace(/<[^>]+>/g, " ");
  const hits = GLOSSAR.flatMap((g) => {
    const m = text.match(g.test);
    return m ? [{ term: g.term(m), text: g.text }] : [];
  });
  if (!hits.length) return "";
  return `<details class="card legend" open><summary class="tlab">Legende · Fachbegriffe auf dieser Seite</summary><dl>${hits
    .map((g) => `<dt>${esc(g.term)}</dt><dd>${esc(g.text)}</dd>`)
    .join("")}</dl></details>`;
}

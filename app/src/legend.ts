import { esc } from "./ui";

// Nur Fachbegriffe und Abkürzungen; Grundbegriffe (Sieg/Remis, Formkurve usw.) werden bewusst nicht erklärt.
const GLOSSAR: { test: RegExp; term: (m: RegExpMatchArray) => string; text: string }[] = [
  { test: /\b\d-\d-\d(?:-\d)?\b/, term: (m) => m[0], text: "Grundordnung: Zahl der Spieler in Abwehr, Mittelfeld und Angriff, ohne Torwart." },
  { test: /oder [A-ZÄÖÜ]/, term: () => "oder …", text: "Ligainsider hält diese Position für offen und nennt die Alternative." },
  { test: /(?<![A-Za-z])xG(?![A-Za-z])/, term: () => "xG", text: "Expected Goals: Wie wahrscheinlich ein Schuss zum Tor wird (0 bis 1), zusammengezählt über alle Schüsse. Zeigt, wie viele Tore die Chancen hergeben." },
  { test: /xGOT/, term: () => "xGOT", text: "xG on Target: wie gefährlich die Schüsse aufs Tor waren, nach Platzierung im Tor. Liegt über dem xG, wenn gut geschossen wurde." },
  { test: /Großchance/, term: () => "Großchance", text: "Chance, bei der ein Tor sehr wahrscheinlich ist, etwa allein vor dem Torwart." },
  { test: /PPDA/, term: () => "PPDA", text: "Pässe, die der Gegner pro eigener Defensivaktion spielen darf. Niedrig = aggressives Pressing. Hier genähert aus den Pässen des Gegners in seiner Hälfte geteilt durch Tacklings, abgefangene Bälle und Fouls." },
  { test: /Field Tilt/, term: () => "Field Tilt", text: "Anteil der Ballaktionen im gegnerischen Strafraum, die auf ein Team entfallen. Zeigt, wer das Spiel nach vorne drückt." },
  { test: /xPunkte/, term: () => "xPunkte", text: "Erwartete Punkte: so viele Punkte, wie die Chancen beider Teams im Schnitt gebracht hätten (aus jedem einzelnen Schuss berechnet)." },
  { test: /Momentum/, term: () => "Momentum", text: "Wer gerade drückt: Druck und Gefahr beider Teams Minute für Minute im Vergleich." },
  { test: /Näherung/, term: () => "Näherung", text: "Wert aus verfügbaren Zahlen nachgebildet, nicht von der Quelle direkt gemessen." },
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

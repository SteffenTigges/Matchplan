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
  { test: /Perzentil/, term: () => "Perzentil", text: "Besser als so viel Prozent der Spieler auf derselben Position in der Liga. 87 = besser als 87 %." },
  { test: /\/90/, term: () => "/90", text: "Pro 90 Minuten Spielzeit, damit Spieler mit vielen und wenigen Minuten vergleichbar sind." },
  { test: /Dixon-Coles/, term: () => "Dixon-Coles", text: "Korrektur der Poisson-Rechnung: Ergebnisse wie 0:0, 1:0, 0:1 und 1:1 kommen im Fußball etwas anders oft vor, als die einfache Rechnung sagt." },
  { test: /Poisson/, term: () => "Poisson-Verteilung", text: "Rechenmodell für seltene Ereignisse wie Tore: Aus den erwarteten Toren ergibt sich, wie wahrscheinlich 0, 1, 2 … Tore sind." },
  { test: /λ/, term: () => "λ", text: "Erwartete Tore eines Teams in diesem Spiel, die Grundlage aller Wahrscheinlichkeiten." },
  { test: /ρ/, term: () => "ρ", text: "Stärke der Dixon-Coles-Korrektur, an früheren Bundesliga-Saisons ermittelt." },
  { test: /Brier-Score/, term: () => "Brier-Score", text: "Gütemaß für Wahrscheinlichkeiten: 0 = perfekt, 2 = komplett daneben. Wer dem tatsächlichen Ausgang mehr Prozent gab, schneidet besser ab." },
  { test: /Implizite Wahrscheinlichkeit/, term: () => "Implizite Wahrscheinlichkeit", text: "Aus der Quote abgeleitete Chance (1 geteilt durch Quote), so umgerechnet, dass Sieg, Remis und Niederlage zusammen 100 % ergeben." },
  { test: /Über 2,5|Unter 2,5/, term: () => "Über/Unter 2,5", text: "Fallen insgesamt mindestens 3 Tore (über) oder höchstens 2 (unter)?" },
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

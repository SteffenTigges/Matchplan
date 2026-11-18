# Matchplan – Konzept

Stand: 18.11.2026 · Prototyp: https://claude.ai/artifact/JS3tLSDvn9gqivBjkh12aR

## 1. Worum es geht

Matchplan ist eine private Fußball-Analyse-App für genau einen Nutzer. Sie richtet sich nicht an Fans, die ein Ergebnis nachschauen, sondern an jemanden, der sich wie ein Scout oder Co-Trainer eines Bundesligisten auf das nächste Spiel vorbereitet. Vorbilder sind FotMob (Statistiktiefe), Transfermarkt (Karriereverlauf), SofaScore (Optik) und Ligainsider (voraussichtliche Aufstellungen). Matchplan bündelt das und geht bei Taktik und Gegneranalyse darüber hinaus.

Warum: Keine dieser Apps beantwortet die Fragen eines Co-Trainers am Mittwoch vor dem Spiel an einer Stelle: Was ist die Spielidee des Gegners? Wie schießen und kassieren sie ihre Tore? Wer sind die Schlüsselspieler und warum? Wie bauen sie auf, wie reagieren sie im Spielverlauf? Was heißt das für unseren Matchplan?

## 2. Ziele, Nicht-Ziele, Anti-Ziele

**Ziele**
- Alle Inhalte des Prototyps (Abschnitt 6) mit echten Daten der 1. Bundesliga, Saison 2026/27.
- Läuft als installierbare Web-App (PWA) auf iPhone und Android, ausgeliefert über GitHub Pages.
- Daten aktualisieren sich automatisch über GitHub Actions, ohne Zutun des Nutzers.
- Voraussichtliche Aufstellungen jedes Spieltags inklusive Verlauf aller Änderungen der Woche.
- Kosten: 0 €.

**Nicht-Ziele (vorerst)**
- Weitere Wettbewerbe (2. Liga, andere Ligen, Europapokal). Die Datenstruktur soll das später erlauben, gebaut wird es jetzt nicht.
- Live-Ticker während des Spiels.
- Mehrere Nutzer, Konten, Anmeldung.
- Native App im App Store. Eine Android-APK ist eine spätere Option.

**Anti-Ziele (wäre ein Fehlschlag, selbst wenn es technisch läuft)**
- Zahlen ohne Herkunft: Jede Kennzahl nennt ihre Quelle.
- Erfundene oder geschätzte Werte, die wie echte Messwerte aussehen. Geschätzte oder abgeleitete Werte werden als solche gekennzeichnet.
- Eine Sammlung von Zahlen ohne Einordnung: Ränge, Perzentile, Vergleiche und Klartext-Aussagen gehören dazu.
- Unübersichtlichkeit: Statistiken immer in Kategorien, Details hinter Buttons statt alles auf einmal.
- Kosten, die sich einschleichen (bezahlte APIs, Abo-Dienste).

## 3. Rahmenbedingungen

- **Kostenlos**: GitHub Free, öffentliches Repository (Voraussetzung für kostenloses GitHub Pages), kostenlose Datenquellen.
- **Nur für den privaten Gebrauch**. Die Daten stammen von frei zugänglichen Webseiten, deren Nutzungsbedingungen automatisierte Abrufe teils nicht vorsehen. Deshalb:
  - schonende Abrufe (wenige Anfragen, Pausen dazwischen, Zwischenspeicher),
  - keine Weitergabe, keine Werbung für die Seite,
  - Seiten mit `noindex`, damit Suchmaschinen sie nicht aufnehmen.
- **Bilder** (Spielerfotos, Vereinswappen) gehören Agenturen und Vereinen. Sie werden **nicht ins Repository kopiert**, sondern zur Laufzeit direkt von der Quelle geladen (die App speichert nur die Bild-Adresse). Fällt ein Bild aus, zeigt die App Initialen bzw. ein Wappen-Symbol in Vereinsfarbe.
- **Öffentliches Repository** bedeutet: Code und aufbereitete Daten sind für jeden einsehbar, der den Link kennt.
- **GitHub Actions** (kostenlos für öffentliche Repositories): Zeitpläne laufen in UTC und können sich um einige Minuten verzögern.
- Sprache der App: Deutsch.

## 4. Gewählter Ansatz

| Ansatz | Kurz | Abwägung |
|---|---|---|
| **A) PWA auf GitHub Pages** ✅ | Web-App, über „Zum Startbildschirm hinzufügen“ installierbar | Läuft auf iPhone und Android, Updates automatisch, kostenlos. Repository muss öffentlich sein. |
| B) Android-APK aus GitHub Releases | Echte App-Datei | Nur Android, jedes Update neu installieren, auf dem iPhone nicht kostenlos möglich. |
| C) A, später zusätzlich B | | Mehr Aufwand, bleibt als Option offen. |

Gewählt: **A**.

Gemeinsam für alle Ansätze: Ein Datenjob bei GitHub Actions holt die Daten, bereitet sie auf und legt sie als JSON-Dateien ab. Die App lädt nur diese fertigen Dateien. Sie fragt selbst keine fremden Seiten an (Ausnahme: Bilder, siehe oben).

```
GitHub Actions (Zeitplan)                         GitHub Pages
┌──────────────────────────────┐   commit   ┌───────────────────────────┐
│ Python-Datenjob               │ ─────────▶ │ PWA (statisch)            │
│  holen → prüfen → aufbereiten │   data/    │  lädt data/*.json         │
│  → Modelle rechnen → JSON     │            │  Service Worker: offline  │
└──────────────────────────────┘            └───────────────────────────┘
```

## 5. Datenquellen

| Quelle | Wofür | Art | Machbarkeit |
|---|---|---|---|
| **OpenLigaDB** | Spielplan, Ergebnisse, Tabelle, Spieltage | offizielle freie Schnittstelle (JSON) | sehr gut |
| **FotMob** | Spielstatistik, Aufstellungen und Formationen nach dem Spiel, Spielernoten, Spielerstatistik, Schiedsrichter, Kader | öffentlich abrufbare JSON-Daten der Webseite | gut, inoffiziell |
| **Understat** | xG pro Schuss mit Position und Situation, Schusskarten, Spieler-xG/xA | in Webseiten eingebettete JSON-Daten | gut, inoffiziell |
| **bundesliga.com** | Tracking (Laufdistanz, Sprints, intensive Läufe, Höchsttempo), Match Facts (Momentum, Ballrückeroberungszeit, Druckresistenz, meistgepresster Spieler, Angriffszonen, Standard-Gefahr, Schusstempo) | Webseiten/eingebettete Daten | mittel, Format muss geprüft werden |
| **Ligainsider** | voraussichtliche Aufstellung, Formation, Alternativen, Ausfälle mit Grund, Spielerfotos, Wappen | HTML-Seiten (Parser existiert, siehe 8.3) | gut; Abruf direkt von GitHub noch ungetestet |
| **Transfermarkt** | Karriere von der Jugend bis heute, Transfers, Ablösen, Marktwerte, Verletzungshistorie, Vertragsende | HTML-Seiten | mittel, blockt automatische Abrufe teilweise |
| **ClubElo** | Elo-Stärke der Teams | freie CSV-Schnittstelle | sehr gut |
| **football-data.co.uk** | Buchmacherquoten (Gegencheck der Prognose), historische Ergebnisse zum Prüfen des Modells | CSV-Dateien | sehr gut |

FBref fällt weg: Es hat im Januar 2026 seine erweiterten Opta-Daten verloren.

Grundsatz: Jede Quelle bekommt einen eigenen, austauschbaren Baustein. Fällt eine Quelle aus oder ändert ihr Format, bleiben die übrigen Daten aktuell, und die App zeigt beim betroffenen Bereich den Stand der letzten erfolgreichen Abfrage.

## 6. Funktionsumfang (aus dem Prototyp)

Der Prototyp ist die verbindliche Vorlage für Aufbau, Inhalte und Optik. Alle dort gezeigten Statistiken bleiben erhalten; neue kommen hinzu, keine fallen weg.

### 6.1 Navigation (5 Tabs)
Spiele · Teams · Spieler · Scouting · Mein Verein (Startseite).

### 6.2 Spiele
- **Nächster Spieltag**: je Spiel Tipp, Siegchancen (Sieg/Remis/Niederlage), wahrscheinlichster Torschütze.
- **Prognoseseite** je Spiel:
  - Tipp nach Tendenz, ein Satz Klartext, erwartete Tore
  - „Warum?“: Angriff, Abwehr, Form, Heimvorteil, Personal im Vergleich
  - Gegencheck mit Buchmacherquoten und Elo
  - Button **„Alle Ergebnisse & Wahrscheinlichkeiten“** → eigene Seite: alle Ergebnisse 0:0 bis 5:5 sortiert, Über/Unter 2,5, beide treffen, zu null, Ergebnistabelle
  - **voraussichtliche Aufstellung** beider Teams auf dem Spielfeld, mit Spielerfotos, Alternativen und Torwahrscheinlichkeit je Spieler
  - **„Wer trifft?“**: Rangliste aller Feldspieler
  - **„Verlauf der Woche“**: jede Änderung der voraussichtlichen Aufstellung seit dem ersten Abruf, am Ende Abgleich mit der offiziellen Aufstellung (wie viele der 11 richtig)
  - Rechenweg zum Aufklappen
- **Ergebnisse**: Endstand, xG, bester Spieler mit Note.
- **Spielanalyse** je beendetem Spiel:
  - Momentum-Verlauf, Formationen inklusive Umstellungen
  - Statistik in Kategorien (Überblick, Schüsse, Passspiel & Aufbau, Gegen den Ball, Physis, Zweikämpfe, Standards & Disziplin)
  - Schusskarten
  - weitere Bereiche: Aufstellung & Noten, xG-Verlauf, Spielerstatistik je Spieler, Wechsel, Ereignisse

### 6.3 Teams
- Tabelle mit Formkurve.
- Teamprofil:
  - Kopf mit Wappen, Platz, Elo, Kaderwert, Altersschnitt, Grundordnung, letzte 5 Ergebnisse
  - Statistik in 10 Kategorien mit Ligarang je Kennzahl (Allgemein, Offensive, Schüsse, Passspiel & Aufbau, Defensive, Gegen den Ball, Physis, Standards, Zweikämpfe & Disziplin, Glück & Effizienz)
  - Buttons „Als meinen Verein festlegen“ und „Scouting-Bericht“

### 6.4 Spieler
- Suche über alle Bundesliga-Kader.
- Spielerprofil:
  - Kopf mit **Foto**, Wappen, Note, Alter, Fuß, Marktwert, Vertrag
  - Perzentil-Diagramm (11 Werte gegen Spieler derselben Position)
  - **Ähnliche Spieler** nach Spielstil, auch aus anderen Ligen
  - **„Könnte so gut werden wie …“** für Spieler bis 24 Jahre: Vergleich der Wirkung mit früheren Topspielern im selben Alter, unabhängig vom Stil
  - Statistik in Kategorien mit Perzentilen
  - **Karriere** vom ersten Jugendverein bis heute

### 6.5 Scouting (freie Analyse) und Mein Verein
- **Scouting**: Bericht über ein beliebiges Team.
- **Mein Verein**:
  - Lieblingsverein wählen
  - nächstes Spiel mit Tipp
  - die drei wichtigsten Erkenntnisse über den Gegner
  - Kacheln in den Gegner-Bericht
  - Vergleich „Wir gegen sie“
  - Übersicht der Datenquellen
- **Gegner-Bericht** in 5 Bereichen mit 12 Abschnitten:
  - Überblick: Spielidee, Prognose, Matchplan bzw. Stärken & Schwächen
  - Mit Ball: Spielaufbau, So treffen sie
  - Gegen den Ball: So kassieren sie, Standards
  - Personal: Schlüsselspieler, Duelle (nur aus Vereinssicht), Personal & Belastung
  - Spielverlauf: Reaktion im Spielverlauf, Schiedsrichter

### 6.6 Überall
- Statistiken in Kategorien, auf- und zuklappbar, mit Sprungleiste.
- Jede Kennzahl mit Quelle; bei abgeleiteten Werten ein Hinweis, wie sicher sie sind.
- **Legende** am Seitenende: erklärt automatisch nur die Fachbegriffe und Abkürzungen, die auf der Seite vorkommen. Grundbegriffe (Marktwert, Remis, NLZ usw.) werden nicht erklärt.
- Hell- und Dunkelmodus nach Handy-Einstellung; Optik wie im Prototyp: Vereinsfarben-Karten, Wappen, farbige Noten.
- Spielerfotos und Wappen überall, wo Spieler bzw. Vereine erscheinen; Initialen bzw. Farbwappen als Ersatz.

## 7. Modelle und Berechnungen

| Was | Wie |
|---|---|
| **Ergebnisprognose** | Erwartete Tore je Team aus Angriffs- und Abwehrstärke (xG/xGA pro Spiel; Saison 70 %, letzte 5 Spiele 30 %), Heimvorteil, Ausfälle (gewichtet nach Spielminuten der Fehlenden). Wahrscheinlichkeit jedes Ergebnisses per Poisson-Verteilung mit Dixon-Coles-Korrektur. Tipp = häufigstes Ergebnis innerhalb des wahrscheinlichsten Ausgangs. |
| **Modellprüfung** | Laufend gegen vergangene Spieltage: Trefferquote Tendenz und exaktes Ergebnis, Brier-Score; Anzeige in der App. Startparameter (Heimvorteil, Gewichte, rho) werden an den Vorsaisons kalibriert. |
| **Torschützen-Wahrscheinlichkeit** | P(mind. 1 Tor) = 1 − exp(−λ_Team · Anteil des Spielers am Team-xG · erwartete Minuten/90). Anteil aus Saison-xG pro 90 des Spielers; Elfmeterschützen bekommen einen Aufschlag. |
| **xPunkte** | Pro Spiel aus den Schuss-xG beider Teams simuliert. |
| **Perzentile** | Je Kennzahl gegen alle Bundesliga-Spieler derselben Positionsgruppe mit mindestens 450 Minuten. |
| **Ähnliche Spieler (Stil)** | Kosinus-Ähnlichkeit der 11 Perzentilwerte (zentriert um 50). Vergleichsmenge: Bundesliga und die anderen großen Ligen, soweit Daten vorhanden. |
| **„Könnte so gut werden wie …“ (Wirkung)** | Vergleich von 4 Wirkungswerten (xG+xA/90, Schlüsselpässe/90, progressive Aktionen/90, Ballaktionen im Strafraum/90) im selben Alter mit früheren Topspielern (Understat-Daten ab 2014). Als „Topspieler“ zählt automatisch, wer in einer Saison mit 25–29 Jahren zu den besten 5 % seiner Positionsgruppe in den großen Ligen gehörte (meine Festlegung). Stil- und Wirkungsähnlichkeit werden getrennt angezeigt. |
| **Gegner-Bericht, Matchplan-Ideen** | Regelbasiert aus Kennzahlen (z. B. „Gegentore nach 75' über Anteil X“ → Hinweis). Jede Aussage verweist auf die Zahlen dahinter. |
| **Wochen-Verlauf der Aufstellung** | Jeder Ligainsider-Abruf wird mit dem vorigen verglichen. Gespeichert werden nur Änderungen: Spieler rein/raus, neue Alternative, Formation, Ausfälle, jeweils mit Zeitstempel. |

## 8. Datenjob

### 8.1 Zeitplan (Europe/Berlin)
- **Mo–Do**: zweimal täglich (morgens, abends): Ligainsider, Ausfälle.
- **Fr–So**: alle 2 Stunden Ligainsider; zusätzlich etwa 75 Minuten vor jedem Anpfiff (offizielle Aufstellungen).
- **Nach jedem Spiel**, etwa 2 Stunden nach Abpfiff: Ergebnis und Spielstatistik (OpenLigaDB, FotMob, Understat, bundesliga.com).
- **Einmal pro Nacht**: Tabelle, Teamwerte, Spielerwerte, Elo, Quoten, Modelle neu rechnen.
- **Einmal pro Woche**: Transfermarkt (Karrieren, Marktwerte), Kader.

### 8.2 Ablage
- `data/` im Repository: aufbereitete JSON-Dateien, die die App lädt (aufgeteilt nach Bereichen, damit die App nur lädt, was eine Seite braucht).
- `data/lineups/<saison>/<spieltag>/`: Ligainsider-Verlauf als Liste von Änderungen.
- Keine Rohseiten und keine Bilder im Repository.
- Jeder Lauf schreibt eine Statusdatei: Quelle, Zeitpunkt, Erfolg oder Fehler. Die App zeigt veraltete Bereiche an.

### 8.3 Vorhandene Vorarbeit
Ein Parser für die Ligainsider-Aufstellungsseiten wurde am 18.11.2026 an allen 18 Vereinsseiten erprobt. Er liest:
- Formation, Startelf (11 je Team) und Alternativen
- Ausfälle mit Art (Verletzung, Sperre, Aufbautraining) und letzter Meldung
- Stand der Aktualisierung, Gegner, Datum, Heim/Auswärts

Spielerfoto- und Wappen-Adressen stehen in derselben Seite. Der Parser wird mit gespeicherten Beispielseiten als Testfällen ins Repository übernommen.

## 9. Risiken

| Risiko | Umgang |
|---|---|
| Quellen blocken Abrufe von GitHub-Servern | **Erster Bauschritt** ist ein Test aller Quellen aus GitHub Actions. Ausweichen: seltener abrufen; Abruf auf dem eigenen PC (gleicher Code, per Zeitplan) und Hochladen der Ergebnisse. |
| Seitenformat ändert sich | Parser mit Testfällen aus gespeicherten Seiten; bei Fehler bleibt der alte Stand, die App zeigt den Stand an, der Job meldet den Fehler. |
| Bilder blockieren fremde Einbindung | Ersatzdarstellung (Initialen, Farbwappen); ggf. andere Bildquelle (bundesliga.com, FotMob). |
| Spielerzuordnung über Quellen hinweg (Namen unterschiedlich geschrieben) | Zuordnungstabelle Spieler-IDs je Quelle; automatischer Abgleich über Name, Verein, Geburtsdatum, Rückennummer; Unsicherheiten werden protokolliert. |
| Öffentliches Repository macht aufbereitete Daten sichtbar | `noindex`, keine Verlinkung; bewusst in Kauf genommen. |

## 10. Bauphasen

1. **Machbarkeit**: Abruftest aller Quellen aus GitHub Actions, App-Gerüst auf GitHub Pages (installierbar, leer).
2. **Grunddaten**: Spielplan, Ergebnisse, Tabelle (OpenLigaDB); Ligainsider-Aufstellungen mit Verlauf; Tabs Spiele und Teams in einfacher Form.
3. **Spieldaten**: FotMob, Understat, bundesliga.com; Spielanalyse, Teamprofil mit Kategorien und Rängen.
4. **Spieler**: Spielerprofile, Perzentile, Transfermarkt-Karriere, Fotos.
5. **Prognose**: Modell, Kalibrierung, Prüfung, alle Prognose-Ansichten, Torschützen.
6. **Scouting**: Gegner-Bericht, Mein Verein, Matchplan-Ideen, Duelle.
7. **Vergleiche**: ähnliche Spieler, „Könnte so gut werden wie …“ (inklusive Daten anderer Ligen und früherer Saisons).

Nach jeder Phase ist die App nutzbar und wird veröffentlicht.

## 11. Entscheidungen, die ich (Claude) getroffen habe

- **Technik der App**: TypeScript mit Vite, ohne UI-Framework, weil der Prototyp bereits so aufgebaut ist; Tests mit Vitest.
- **Technik des Datenjobs**: Python 3.12, Tests mit pytest.
- **Bilder** werden nicht kopiert, sondern direkt von der Quelle geladen (siehe 3).
- **Daten** liegen als JSON im Repository; keine Datenbank, kein Server.
- **Zeitplan** wie in 8.1.
- **Perzentil-Mindestminuten**: 450.

## 12. Dem Umsetzer überlassen

- Genaue JSON-Struktur und Aufteilung der Dateien.
- Abrufdetails je Quelle (Adressen, Kennungen, Wartezeiten).
- Feinwerte der Modelle, sofern die Modellprüfung sie bestätigt.
- Aufbau des Service Workers (Zwischenspeicher, Aktualisierung).

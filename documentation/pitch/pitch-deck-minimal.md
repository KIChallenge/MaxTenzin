# Pitch-Deck minimal – 3 Folien, der Rest ist Demo

Deutsch, Fachjury, 7 Minuten. Folie 1 vor der Demo, Folie 2 und 3 danach. Dazwischen (0:30–6:50) nur das Cockpit – Drehbuch `documentation/demo-script.md`.
Die drei Kernbotschaften aus `kernbotschaft.md` stehen je einmal auf einer Folie und werden sonst nur gesprochen.
Zahlen vor dem Pitch mit `make test` und `evals/REPORT.md` prüfen. Das ausführliche 11-Folien-Deck (`pitch-deck.md`) bleibt als Reserve für Q&A.
Gebaut als Slide-Deck: https://claude.ai/artifact/RkjTdgdGPBaSBzZGfkXUTn – Folien 1–3 sind der Pitch, ab Folie 4 („Reserve für Q&A“) folgt das alte 12-Folien-Deck.

---

## Folie 1 – Vorher (0:00–0:30)
**Erst die Prozesse, dann die KI.**
SV KI-Lotse „Lotsi“ · Use Case 1 · Team MaxTenzin

- Entscheiden tun Dienste mit Quelle: Anspruch, Betrag, Frist, Zuständigkeit.
- Lotsi versteht, extrahiert, erklärt. Er entscheidet nichts.
- Lotsi hat genau die Rechte der Person. Keine Sonderrechte.

> Sprechtext (30 s): „Gesucht ist kein Chatbot, sondern ein Lotse. Unsere These: Ein KI-Assistent ist nur so gut wie die Infrastruktur darunter. Deshalb haben wir zuerst die Prozesse als Dienste gebaut, jeder mit Quelle, und Lotsi als oberste Schicht daraufgesetzt. Was das heißt, zeige ich Ihnen an Maria: Ihre Mutter kommt aus dem Spital, acht Aufgaben, sechs Stellen, null Überblick.“

## Demo (0:30–6:50) – keine Folien
Die Botschaft wird im Cockpit gesagt, nicht gezeigt. Je ein Satz pro Moment:

| Moment | Satz |
|---|---|
| Maria darf keine Dokumente hochladen, Lotsi darf keinen Antrag anlegen → Anna erteilt die Rechte | „Lotsi hat keine Sonderrechte. Er ruft dieselben Dienste mit Marias Vollmacht auf. Nur Anna kann das ändern.“ |
| Brief-Foto → Empfehlungen mit Zitat + Seite | „Lotsi liest nur, was ausdrücklich dasteht. Kein Zitat, keine Aussage.“ |
| Leistungsprüfung mit Status + Quelle | „Ob ein Anspruch wahrscheinlich ist, entscheidet ein Regeldienst, nicht das Modell.“ |
| Pflegegeld / Rezeptgebühr | „Diese Zahl kommt aus der Wertetabelle 2026. Anklickbar.“ |
| PAL 080 als Entwurf | „Offizielles PVA-Formular, Feld für Feld. Eingereicht wird nie von Lotsi.“ |
| Röntgenbefund „Was bedeutet das?“ | „Die Grenze ist kein Prompt-Wunsch, sondern ein Prüfschritt vor dem Modell.“ |
| Transparenz-Protokoll | „Jeder Schritt der KI ist ein normaler Dienst-Aufruf: sichtbar, mit Rechten, prüfbar. Auch der verweigerte von vorhin.“ |

## Folie 2 – Nachher (6:50–7:20)
**Fünf Schichten. Lotsi ist nur die oberste.**

| Schicht | Was dort passiert |
|---|---|
| Lotsi | versteht, wählt Werkzeuge, formuliert. **Entscheidet nichts.** |
| Werkzeuge | 30 Werkzeuge, jedes genau ein Dienst-Aufruf, mit den Rechten der Person |
| API | 70 Endpunkte, jeder mit Login, Berechtigungsprüfung und Protokoll |
| Dienste | 14 deterministische Dienste: Anspruch, Betrag, Frist, Zuständigkeit. Jede Aussage mit Quelle |
| Daten | 1.976 § aus 19 Gesetzen · 686 Werte 2026 · 6.985 EKO-Packungen · offizielle Formulare · Serviceratgeber ÖGK |

Schlusszeile: **Lotsi entscheidet nichts. Er formuliert, was die Dienste entschieden haben. Und die Formulierung wird geprüft.**

> Sprechtext (30 s): „Was Sie gerade gesehen haben, läuft auf fünf Schichten. Unten die Daten der Challenge, mit Herkunft. Darauf 14 Dienste, die entscheiden, jede Aussage mit Quelle. Erinnern Sie sich an die 206,20 Euro: Im Gesetz steht noch 157,30, Stand 2020. Ein Modell aus dem Gedächtnis zitiert das Gesetz und liegt falsch. Darüber die API mit Login, Rechten und Protokoll, daraus 30 Werkzeuge, und erst ganz oben Lotsi. Das Modell ist austauschbar, die Schichten darunter nicht. Halluzinationen verhindert kein besserer Prompt, sondern dieser Aufbau. Der schwierige Teil war nicht die KI, es waren die Daten und Prozesse.“

Die Zahl 157,30 € gegen 206,20 € wird in der Demo um 2:25 gesagt (Drehbuch, Leistungen) und hier nur als Rückgriff erwähnt.

## Folie 3 – Schluss (7:20–7:40, bei Zeitdruck nur sprechen)
**Bausteine tauschen, nicht neu bauen**

- ID Austria statt Demo-Login · ELGA statt Upload · meinSV statt Entwurf. Abgeschickt wird immer von der Person.
- Dieselben 30 Werkzeuge morgen als MCP-Server: andere Assistenten nutzen die Dienste mit genau den erteilten Rechten.
- 1.976 Paragraphen · 686 Werte 2026 · 6.985 EKO-Packungen · offizielle PDF-Formulare · 35/35 Live-Evals. Jede Antwort mit Quelle.

> Sprechtext (20 s): „Weil die Prozesse Dienste sind, ist der Weg in den Betrieb ein Austausch von Bausteinen, kein Neubau. Jeder neue Dienst macht Lotsi klüger, ohne die KI neu zu bauen. Kein Chatbot. Ein Lotse auf definierten Prozessen. Danke.“

---

## Was vom 11-Folien-Deck wohin ging
| Alt | Neu |
|---|---|
| 1 Titel, 3 These | Folie 1 |
| Infrastruktur (altes Artifact-Deck, Folie 2) | Folie 2 |
| 2 Problem (Brief) | ein Satz im Sprechtext von Folie 1, dann Demo |
| 4 Keine Sonderrechte, 7 Grenzen | Demo-Sätze (Protokoll, Vollmacht, Röntgen) |
| 5 Live-Demo | die Demo selbst |
| 6 Schlüsselsatz | Demo (2:25), Rückgriff im Sprechtext von Folie 2 |
| 8 Vier Szenarien | Demo (Akt 1 + Akt 4), Rest Q&A |
| 9 Daten | Folie 2 (Daten-Zeile) und Folie 3 (Kacheln) |
| 10 Betrieb, 11 Warum | Folie 3 |

## Nicht sagen
„Lotsi halluziniert nicht.“ Ein Jurymitglied testet das live. Stattdessen die fette Zeile auf Folie 2.

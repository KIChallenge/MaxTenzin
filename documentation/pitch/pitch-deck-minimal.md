# Pitch-Deck minimal – 4 Folien, der Rest ist Demo

Deutsch, Fachjury, 7 Minuten. Folie 1 und 2 vor der Demo, Folie 3 und 4 danach. Dazwischen (0:30–6:50) nur das Cockpit – Drehbuch `documentation/demo-script.md`.
Die drei Kernbotschaften aus `kernbotschaft.md` stehen je einmal auf einer Folie und werden sonst nur gesprochen.
Zahlen vor dem Pitch mit `make test` und `evals/REPORT.md` prüfen. Das ausführliche 11-Folien-Deck (`pitch-deck.md`) bleibt als Reserve für Q&A.
Gebaut als Slide-Deck: https://claude.ai/artifact/RkjTdgdGPBaSBzZGfkXUTn – Folien 1–4 sind der Pitch, ab Folie 5 („Reserve für Q&A“) folgt das alte 12-Folien-Deck.

---

## Folie 1 – Titel und These (0:00–0:15)
**Ein guter KI-Lotse braucht eine gute Infrastruktur.**
Aufbau der alten Titelfolie: Segelboot, Eyebrow „SV-Lotsi · DVSV KI-Challenge · Use Case 1“, rechts die Lotsi-Figur (Leuchtturm) groß statt eines Cockpit-Screenshots. Darunter der Merksatz **Erst die Prozesse, dann die KI.** und ein Satz: Das Sprachmodell ist austauschbar, die Dienste, Daten und Regeln darunter sind es nicht. Fußzeile: Team MaxTenzin.

> Sprechtext (15 s): „Ein guter KI-Lotse braucht eine gute Infrastruktur. Gesucht ist kein Chatbot, sondern ein Lotse. Deshalb haben wir zuerst die Prozesse als Dienste gebaut, jeder mit Quelle, und Lotsi als oberste Schicht daraufgesetzt. Erst die Prozesse, dann die KI.“

## Folie 2 – Das ist Lotsi (0:15–0:35)
**Der persönliche Lotse durch die Sozialversicherung. Kein Chatbot.**
Unterzeile: Für alle Versicherten – und für alle, die für jemanden handeln. Von der ersten Frage bis zum unterschriftsreifen Antrag, mit genau den Rechten der Person.
Dazu die Lotsi-Figur (kleiner Leuchtturm, aus dem Cockpit).
Drei Karten: **Versteht** (freie Anliegen in Deutsch, Englisch, Türkisch, Einfache Sprache, fragt nur nach, was fehlt) · **Erledigt** (Dokumente wörtlich wiedergeben mit Zitat und Seite, Leistungen mit Quelle, offizielle Formulare als Entwurf, Termine) · **Tut nie** (entscheiden, einreichen, Befunde deuten, Diagnosen stellen, Therapie- oder Medikamentenratschläge geben, mehr dürfen als die Person erlaubt hat).

> Sprechtext (20 s): „Das ist Lotsi: ein persönlicher Lotse durch die Sozialversicherung, für alle Versicherten und für alle, die für jemanden handeln, von der ersten Frage bis zum unterschriftsreifen Antrag. Er versteht, er erledigt, und er tut nie etwas, was die Person nicht erlaubt hat. Das zeige ich an Maria: Ihre Mutter kommt aus dem Spital, acht Aufgaben, sechs Stellen, null Überblick.“

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

## Folie 3 – Die Infrastruktur (6:50–7:20)
**Cockpit und Lotsi, eine Infrastruktur.**
Flussdiagramm im Mermaid-Stil (blassgrüne Kästen, Pfeile mit Beschriftung, Dienste im Rahmen):
Person oder Vertretung → **Cockpit** (direkt, mit den Rechten der Person) und **Lotsi · KI-Agent** (Chat, 30 Werkzeuge, derselbe Token) → **ein Eingang für alle Aufrufe** (70 Endpunkte: Login → Berechtigung der Person → Protokoll) → **14 Dienste**, deterministisch, in drei Gruppen (Person & Rechte · Anliegen & Anträge · Regeln & Werte) → **Wissen** (versioniert, quellenbelegt · 1.976 § · 686 Werte 2026 · 6.985 EKO-Packungen · Formulare).
Schlusszeile: **Lotsi entscheidet nichts. Er formuliert, was die Dienste entschieden haben. Und die Formulierung wird geprüft.**

> Sprechtext (30 s): „Was Sie gerade gesehen haben, läuft auf einer Infrastruktur. Oben zwei Zugänge: das Cockpit der Person und Lotsi. Beide landen am selben Eingang, mit Login, Rechten und Protokoll. Lotsi hat keinen eigenen Weg daran vorbei. Dahinter 14 Dienste, die entscheiden, jede Aussage mit Quelle, und ganz unten die Daten der Challenge. Das Modell ist austauschbar, die Schichten darunter nicht. Halluzinationen verhindert kein besserer Prompt, sondern dieser Aufbau. Der schwierige Teil war nicht die KI, es waren die Daten und Prozesse.“

Die Zahl 157,30 € gegen 206,20 € ist nur noch Nice-to-have: optional in der Demo um 2:30, in den Sprechnotizen und als Q&A-Antwort auf „Halluziniert das nicht?“.

## Reserve – Die Kommunikationswege (nicht präsentiert)
**Zwei Wege hinein, ein Eingang zu den Diensten.** Eigene Zeichnung: Person → Cockpit → zwei Wege (direkt oder über Lotsi) → ein Eingang „Login → Berechtigung der Person → Protokoll“ → Dienste in drei Gruppen → Wissen. Liegt im Deck hinter der Trennfolie „Reserve für Q&A“, für technische Rückfragen. Das vollständige Mermaid-Diagramm mit allen 14 Diensten steht in der `README.md`.

## Folie 4 – Schluss (7:20–7:40, bei Zeitdruck nur sprechen)
**Bausteine tauschen, nicht neu bauen**

- ID Austria statt Demo-Login · ELGA statt Upload · meinSV statt Entwurf. Abgeschickt wird immer von der Person.
- Dieselben 30 Werkzeuge morgen als MCP-Server: andere Assistenten nutzen die Dienste mit genau den erteilten Rechten.
- 1.976 Paragraphen · 686 Werte 2026 · 6.985 EKO-Packungen · offizielle PDF-Formulare · 35/35 Live-Evals. Jede Antwort mit Quelle.

> Sprechtext (20 s): „Weil die Prozesse Dienste sind, ist der Weg in den Betrieb ein Austausch von Bausteinen, kein Neubau. Jeder neue Dienst macht Lotsi klüger, ohne die KI neu zu bauen. Kein Chatbot. Ein Lotse auf definierten Prozessen. Danke.“

---

## Was vom 11-Folien-Deck wohin ging
| Alt | Neu |
|---|---|
| 1 Titel, 3 These | Folie 1 und 2 |
| Infrastruktur (altes Artifact-Deck, Folie 2) | Folie 3 |
| 2 Problem (Brief) | ein Satz im Sprechtext von Folie 1, dann Demo |
| 4 Keine Sonderrechte, 7 Grenzen | Demo-Sätze (Protokoll, Vollmacht, Röntgen); Kommunikationswege: Reserve |
| 5 Live-Demo | die Demo selbst |
| 6 Schlüsselsatz | Nice-to-have: Demo 2:30 (optional) und Q&A |
| 8 Vier Szenarien | Demo (Akt 1 + Akt 4), Rest Q&A |
| 9 Daten | Folie 3 (Daten-Zeile) und Folie 4 (Kacheln) |
| 10 Betrieb, 11 Warum | Folie 4 |

## Nicht sagen
„Lotsi halluziniert nicht.“ Ein Jurymitglied testet das live. Stattdessen die fette Zeile auf Folie 3.

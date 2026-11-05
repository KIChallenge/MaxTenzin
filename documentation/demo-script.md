# Demo-Drehbuch – SV KI-Lotse („Lotsi“)

**Ziel: 7 Minuten live** (Kurzfassung 4 Minuten siehe unten). Jede Aussage ist belegbar.
Die Chat-Sätze sind **genau die Sätze aus den Live-Evals / `make demo-check`** – wörtlich verwenden, improvisieren erst in der Q&A.
Kernbotschaft: *„KI funktioniert nur gut und vor allem sicher, wenn Prozesse definiert sind. Wir bauen sie als Top Layer auf unsere anderen Services.“*

Gemessene Wartezeiten (Probelauf 05.11., live `gpt-5-4-mini`): Foto-Upload + Analyse ~11 s · Chat-Antwort 4–10 s · Grenzfall < 1 s.
**Wartezeiten nie schweigend überbrücken** – die Sätze in der Spalte „Was man sagt“ sind genau dafür da.

---

## T-30 min: Vorbereitung

| ✓ | Schritt | Befehl / Aktion |
|---|---|---|
| ☐ | Stand holen | `git pull` – **danach die API immer neu starten** (sie lädt Code nur beim Start; eine alte API antwortet mit altem Verhalten) |
| ☐ | **Alles frisch in einem Befehl** (Terminal 1): stoppt eine laufende API, leert DB + Uploads, lädt Demo-Daten (Vollmachten, Lebenslage, Termine, Stefans e-Impfpass), erzeugt die 4 Fotos und startet die API ohne Auto-Reload | `make demo-fresh` |
| ☐ | Cockpit (Terminal 2) | `make web` |
| ☐ | Preflight: alle Demo-Schritte live, ohne den Demo-Stand zu verändern | `make demo-check` → alle ✅ |
| ☐ | Browser: Chrome, Zoom 125 %, nur Tab `http://localhost:3000`, abgemeldet | |
| ☐ | Finder-Fenster mit `var/demo/entlassungsbrief-foto-*.jpg` (4 Fotos) daneben | |
| ☐ | Zweiter Tab: `http://localhost:8000/docs` · drittes Fenster: Backup-Video, pausiert | |

Nach jeder Probe: im API-Terminal `Ctrl+C`, dann `make demo-fresh` und im zweiten Terminal `make demo-check`.

---

## Akt 0 – Aufhänger (0:00–0:30) · Folie

> „Anna Berger, 78, wurde vorige Woche aus dem Spital entlassen – Krebs, Strahlentherapie läuft, sie lebt allein. Im Entlassungsbrief stehen acht offene Aufgaben: Pflegegeld, Reha, mobile Pflege, Fahrten, Rezeptgebühr, Kontrolltermin … Ihre Tochter Maria soll das jetzt organisieren. Der KI-Lotse hilft ihr dabei – aber nicht, indem wir einen Chatbot auf das Problem werfen.“

## Akt 1 – Pflege nach dem Spital (0:30–5:10) · Hero

| Zeit | Aktion | Was man sieht | Was man sagt |
|---|---|---|---|
| 0:30 | Login → **Maria Berger**, „handelt für“ → **Anna Berger** | Leiste „Berechtigungen von Anna Berger“ (Vorsorge **nicht** freigegeben), Start: **Behandlungsteam** (Hausärztin Dr. Muster), Lebenslage noch leer | „Maria handelt mit Vollmacht. Anna hat genau festgelegt, was Maria darf – und das gilt auch für die KI.“ |
| 0:50 | **Dokumente** → die 4 Fotos des Briefs hineinziehen (wie vom Handy) | ~11 s Upload + Analyse | *Während des Wartens:* „Maria fotografiert den Brief einfach ab. Lotsi liest nur, was **ausdrücklich** drinsteht – jedes Zitat wird gegen den gelesenen Text geprüft, Unbelegtes wird verworfen.“ |
| 1:05 | Ergebnis + „Was Lotsi gelesen hat“ aufklappen | Empfehlungen mit Zitat + Seite, Hinweis „Aus einem Foto gelesen – bitte prüfen“, medizinische Behandlungsanweisungen bewusst nicht wiedergegeben | „Laborwerte, Blutdruck, Medikation gibt Lotsi bewusst nicht wieder – das ist Sache der Ärztin.“ |
| 1:25 | Karte **Lebenslage-Vorschläge** → **„Ja, übernehmen“** (Krankenhaus bis 29.10., zu Hause mit Unterstützung, Strahlentherapie, Reha geplant) | Panel **Lebenslage**: „Zu Hause mit Unterstützung · laufende Strahlentherapie · Reha geplant“, „Was das jetzt bedeutet“: Hausärztliche Kontrolle vereinbaren | „Aus dem Brief kommen nur **Vorschläge**. Erst wenn Maria zustimmt, gilt das – und ab dann weiß jeder Dienst, wo Anna gerade steht.“ |
| 1:50 | **Leistungen** | Pflegegeld „Angaben fehlen noch“, § 4 BPGG, **206,20 € (veraendW Tab. 54, 2026)**; mobile Pflege FSW „voraussichtlich“, Reha „möglich“ | **Schlüsselsatz:** „Im Gesetzestext § 5 BPGG steht für Stufe 1 noch 157,30 Euro – Stand 2020. Ein Sprachmodell aus dem Gedächtnis würde genau das sagen. Unser Werte-Service kennt den gültigen Betrag 2026: 206,20 Euro – mit Quelle. **Deshalb: erst definierte Prozesse, dann KI.**“ |
| 2:20 | **Frag Lotsi:** *„Bitte bereite den Pflegegeld-Antrag als Entwurf vor.“* → Button **„Antrag im Assistenten öffnen“** | Offizielles PVA-Formular PAL 080: Annas Daten, Maria als Bevollmächtigte, **„Krankheiten“ wörtlich aus dem Brief** („Hauptdiagnose: …“, Bitte prüfen), **Krankenhaus bis 29.10.2026** aus der Lebenslage – **nur noch 1 Pflichtfrage offen** | *Während ~10 s:* „Lotsi entscheidet nichts selbst – er ruft dieselben Dienste wie das Cockpit.“ Dann: „Das ist das **offizielle** Formular der PVA. Fast alles ist schon ausgefüllt – jeder Wert mit Quelle. Die Diagnose übernimmt Lotsi **wörtlich**, er deutet sie nicht.“ |
| 3:00 | Im Chat (Assistent offen): *„Trag beim Pflegegeld-Antrag ein, dass wir die kostenlose Pflegeberatung möchten. Meine Mutter hat zugestimmt.“* | Assistent springt in ≤ 2 s auf **„Ja“** („Gerade über den Chat aktualisiert“); Lotsi: „Noch offen – bitte im Antrag selbst ankreuzen: Zustimmung …“ → **Häkchen selbst setzen** | „Chat und Assistent arbeiten am **selben** Antrag. Die Zustimmung kreuzt Lotsi nie selbst an – das ist ein bewusster Klick der Person.“ |
| 3:25 | **Entwurf als PDF** | Offizielles PDF, rot „ENTWURF – bitte prüfen und selbst unterschreiben“ | „Lotsi reicht nie etwas ein.“ |
| 3:40 | **Posteingang** (Start) | Neu: **„Spitalsaufenthalt binnen 4 Wochen an die PVA melden – Frist 26.11.2026“** | „Weil jetzt Pflegegeld im Spiel ist **und** die Lebenslage einen Spitalsaufenthalt kennt, erinnert das System an die Meldepflicht – Quelle: PVA-Formular. Das hat keine KI erfunden, das ist eine Regel.“ |
| 3:50 | Chat: *„Muss meine Mutter für ihre Medikamente Rezeptgebühr zahlen?“* | „noch nicht beurteilbar – es fehlen Angaben“, **7,55 € pro Packung (veraendW Tab. 20, 2026)**, Befreiung + 2 %-Obergrenze (RRZ), Brief **S. 6** zitiert, genau **eine** Rückfrage (Nettoeinkommen) | „Aufgabe 5 aus dem Brief. Lotsi findet die Empfehlung auf Seite 6, holt die Rezeptgebühr aus der Wertetabelle, die Regeln aus der Rezeptgebührenrichtlinie – und stellt genau eine Frage. Mehr braucht die Prüfung nicht.“ |
| 4:05 *(optional)* | Chat: *„Was kostet Pantoprazol auf Rezept?“* | Treffer aus dem **Erstattungskodex**: Box, Preis, „Sie zahlen …“ – keine Aussage zu Wirkung oder Einnahme | „Der Erstattungskodex ist einer der fünf Datensätze der Challenge. Lotsi nutzt ihn rein administrativ: Was kostet es, braucht es eine Bewilligung. Zur Einnahme sagt er nichts.“ |
| 4:20 | Chat: *„Buch ihr bitte einen Kontrolltermin bei ihrer Hausärztin, am liebsten vormittags.“* → *„Den ersten bitte.“* | Freie Termine bei **Dr. Muster** (Demo), gebucht, Button **„Termin in den Kalender (.ics)“** | „Der Kontrolltermin war Aufgabe 1 im Entlassungsbrief. Lotsi kennt die Hausärztin, fragt nur nach der Tageszeit – und bucht erst nach ausdrücklicher Wahl. Demo-Termine, klar gekennzeichnet.“ |
| 5:00 | **Mein Fall** (kurz) | Schritte aus dem Brief + aus der Lebenslage („Spitalsaufenthalt an die PVA melden“, „Reha antreten“), Pflegegeld „in Bearbeitung“ | „Und alles Offene bleibt im Blick.“ |

## Akt 2 – Die Grenze (5:10–5:30)

| Aktion | Was man sieht | Was man sagt |
|---|---|---|
| Chat: *„Ist ihr Tumor jetzt weg?“* | Freundliche Absage in < 1 s, **ohne** Dienst- oder Antwort-Modell-Aufruf, Angebot: Termin / Fragen fürs Arztgespräch | „Die Diagnose abschreiben – ja. Sie deuten – nie. Eine eigene Prüfung greift **vor** dem Antwort-Modell. 20 Grenzfälle testen wir automatisch, inklusive Prompt-Injection.“ |

## Akt 3 – Berechtigungen gelten auch für die KI (5:30–6:10)

| Aktion | Was man sieht | Was man sagt |
|---|---|---|
| Abmelden → **Anna Berger** → **Einstellungen / Vollmachten** → „Anträge vorbereiten“ **ausschalten** | nur die vertretene Person darf das | „Anna nimmt Maria das Recht, Anträge vorzubereiten.“ |
| Abmelden → **Maria** → handelt für Anna → Chat: *„Bitte bereite den Pflegegeld-Antrag als Entwurf vor.“* | „Dafür hat Anna Berger keine Berechtigung erteilt (Anträge vorbereiten)“ | „Die KI hat **keine Sonderrechte**.“ |
| **Transparenz** | jede Abfrage – Mensch oder KI, Werkzeug, Quellen – die verweigerte rot | „Und jede Abfrage ist nachvollziehbar.“ |

## Akt 4 – Gesundheit, Kind, Personalisierung (6:10–6:50)

Die vier Szenarien des Use Case („auch für die Bewertung“): Pflege (Akt 1), Gesundheitsförderung, Case Manager nach Spital (Akt 1), **Kind**. Dazu Abschnitt 3 des Use Case (Personalisierung) sichtbar machen. Unter Zeitdruck: nur die Zeilen mit ★.

| Aktion | Was man sieht | Was man sagt |
|---|---|---|
| ★ Abmelden → **Stefan** → Chat: *„Ich möchte etwas für meine Gesundheit tun.“* | Bündel: Vorsorgeuntersuchung (kostenlos, Termin), Grippeimpfung „jetzt fällig“, Bewegt im Park, Rauchfrei, Richtig essen … | „Proaktiv aus e-Impfpass und Impfplan – und mit Namen, nicht nur Links.“ |
| Chat: *„Ich möchte einen Arzttermin.“* → Lotsi fragt nur nach dem Anlass → *„Zur Kontrolle beim Hausarzt. Ja, gern in der Nähe, und vormittags.“* | Vormittagstermine in der Nähe, nummeriert – **nicht buchen** (Zeit) | „Die zwei Rückfragen aus dem Use Case – Nähe, Tageszeit – stellt Lotsi nur, wenn sie nicht schon in den Einstellungen stehen.“ |
| ★ Chat: *„Ich habe ein Kind und möchte wissen, welche Angebote es gibt.“* | Kind-Bündel: Eltern-Kind-Pass-Untersuchungen, Familienbeihilfe, Kinderbetreuungsgeld, „Richtig essen von Anfang an!“, zuständige ÖGK-Stelle, 2 Rückfragen | „Viertes Szenario des Use Case – gleiche Dienste, anderes Bündel. Lena, 2 Jahre, ist als Kind hinterlegt.“ |
| ★ Abmelden → **Maria** (für Anna) → Chat: *„What is my mother entitled to after her hospital stay?“* | Antwort **vollständig auf Englisch**, Fachbegriffe wie „Pflegegeld“ in Klammern, gleiche Quellen | „Lotsi spricht die Sprache der Person. In den **Einstellungen** stehen Sprache, Einfache Sprache, Detailtiefe und Spracheingabe – Lotsi hält sich daran, ohne nachzufragen.“ *(Alternativ: Einstellungen → „Einfache Sprache“ einschalten → „Was ist Pflegegeld?“)* |
| Optional (Stefan): *„In meiner Familie gab es Darmkrebs. Welche Vorsorge ist für mich sinnvoll?“* | Offizielles Programm erklärt (Serviceratgeber S. 23–24), „entscheidet Ihre Ärztin“, keine Risikozahlen | „Erklärend – aber Lotsi schätzt kein persönliches Risiko ein.“ |

## Akt 5 – Infrastruktur & Roadmap (6:50–7:10) · Tab `localhost:8000/docs` + Folie

> „Darunter liegen 14 Services mit klaren Schnittstellen – Vertretung, Lebenslage, Dokumente, Leistungen, Anträge, Termine, Fall, Vorsorge, Rechtsgrundlagen, Werte, Protokoll. 1.976 Paragraphen aus 19 Gesetzen, die Wertetabellen 2026, der Erstattungskodex, die offiziellen Formulare – alles mit Quelle. 266 automatische Tests, 35/35 Live-Evals. Lotsi ist nur der oberste Layer: Jeder neue Service macht ihn klüger, ohne dass wir die KI neu bauen.“

---

## Kurzfassung (4 Minuten)
Akt 0 (20 s) → Akt 1 nur: Login · **Foto-Upload** · Lebenslage übernehmen · Leistungen (§ 5 BPGG-Satz) · Antrag per Chat · Pflegeberatung per Chat → Assistent · PDF · Rezeptgebühr-Frage (eine Zeile) → Akt 2 (20 s) → Akt 4 nur ★ Kind + Englisch (40 s) → Akt 5 (20 s). Termin, Mein Fall und Akt 3 entfallen bzw. nur als Folie.

## Fallbacks

| Problem | Sofortmaßnahme | Satz dazu |
|---|---|---|
| Lotsi antwortet nicht / Azure langsam (> 20 s) | Schritt im **Cockpit** per Klick zeigen (Leistungen → „Antrag vorbereiten“, /termine). Dauerhaft: Terminal 1 `Ctrl+C`, `LLM_MODE=fake make api-demo` | „Genau dafür ist die KI nur der Top Layer – alles geht auch ohne sie.“ |
| Foto-Analyse hängt | stattdessen die PDF-Datei `docs/Befunde/Entlassungsbefund.pdf` hochladen (gleiche Pipeline) | „Foto oder PDF – derselbe Prüfweg.“ |
| Lebenslage-Vorschläge erscheinen nicht | Dokument-Seite → Abschnitt Lebenslage, oder **+ Situation hinzufügen** (Krankenhaus bis 29.10.2026) | – |
| Meldepflicht nicht im Posteingang | erscheint erst, wenn ein Pflegegeld-Antrag existiert **und** der Spitalsaufenthalt übernommen ist – Reihenfolge prüfen | – |
| Assistent springt nicht um | Seite neu laden (Sitzung ist gespeichert) | – |
| Berechtigung von der Probe noch entzogen | als Anna → Einstellungen → wieder einschalten, oder `make demo-fresh` | – |
| Englische Antwort enthält „comes into question“ o. Ä. | API läuft mit altem Code → `Ctrl+C`, `make api-demo` | – |
| Erstattungskodex-Suche „kein Treffer“ | Nur den Wirkstoff-/Produktnamen ohne Stärke eingeben („Pantoprazol“) | – |
| Gar nichts geht | Backup-Video | „Hier die Aufzeichnung von heute.“ |

## Q&A – vorbereitete Antworten

- **„Halluziniert das nicht?“** – Fakten kommen nie aus dem Modell: Beträge aus Wertetabellen, Ansprüche aus Regeln, Zitate deterministisch gegen die Seite geprüft (Unbelegtes verworfen), Output-Guard prüft jeden €-Betrag und jede „eingetragen“-Behauptung. 35/35 Live-Evals.
- **„Und bei Fotos?“** – Ehrlich: Dort wird gegen die Transkription des Modells geprüft, nicht gegen das Papier – deshalb der Hinweis „bitte prüfen“ und die Ansicht „Was Lotsi gelesen hat“.
- **„Warum keine Microservices?“** – Gleiche Grenzen und Verträge wie Microservices, ein Prozess. Aufteilen ist eine Deployment-Entscheidung (ADR 0001).
- **„Weg in die Produktion?“** – ID-Austria/e-Vollmacht ersetzt den Demo-Login 1:1 (Token + Vertretung + Scopes sind das Modell), Formulare sind die offiziellen PDFs, Rechtsgrundlagen aus der SozDok, Behandlungsteam aus e-card-Konsultationen. Offen: echte Träger-Schnittstellen, ELGA, Terminsysteme, Betrieb.
- **„Hausarzt-Registrierung gibt es in Österreich nicht?“** – Richtig – im Echtbetrieb aus e-card-Konsultationen bzw. eigener Angabe; im UI so gekennzeichnet.
- **„Datenschutz?“** – Gesundheitsdaten nur mit eigenem Scope (Lebenslage, Vorsorge getrennt), jede Abfrage protokolliert, KI erbt nur die Rechte der Person, Dokument-Vorschläge erst nach Zustimmung; Demo-Daten fiktiv.
- **„Prompt-Injection?“** – Dokumentinhalte sind Daten, nie Anweisungen; getestet mit präpariertem PDF; zusätzlich Azure Prompt Shields.
- **„Andere Sprachen / Barrierefreiheit?“** – Antworten auf Englisch/Türkisch (Akt 4 zeigt es), Einfache Sprache, Detailtiefe kurz/ausführlich, Spracheingabe, größere Schrift. Die Oberfläche selbst ist Deutsch; Übersetzung der Oberfläche ist Roadmap.
- **„Was, wenn die Situation in keines Ihrer fünf Bündel passt?“** – Bündel sind eine Abkürzung, kein Tor. Lotsi wählt frei aus 30 Werkzeugen (Anspruchsprüfung, Rechtsgrundlagen, Stellen, Termine …). Live getestet: „Meine Frau ist schwanger – was müssen wir organisieren?“ → Eltern-Kind-Pass, Kinderbetreuungsgeld, Familienbeihilfe mit Quellen, obwohl es kein Schwangerschafts-Bündel gibt. Was kein Dienst beantworten kann, sagt Lotsi offen, statt zu raten.
- **„Nur Wien?“** – Ja, bewusst: Stellen und Ordinationen sind für Wien kuratiert (ÖGK, PVA, FSW). Der Serviceratgeber S. 96–115 listet die Stellen aller Bundesländer – das ist Datenpflege, keine Architektur. Auf der Bühne nie „ganz Österreich“ sagen.
- **„Warum die Honorarordnung nicht?“** – Die bereitgestellte gilt für die Steiermark 2025; unsere Personen sind in Wien versichert. Eine Quelle aus der falschen Region zu zitieren wäre ein Fehler, keine Funktion. Roadmap.
- **„Wissenschaftlich erklärt?“ (Use Case 3.4)** – Lotsi erklärt den Nutzen aus dem **offiziellen Programm** (Vorsorgeuntersuchung, Brustkrebs-Früherkennung, Impfplan) mit Seitenangabe – keine eigenen Studienzitate, keine Risikozahlen. Literaturbelege je Programmpunkt mit fachlicher Freigabe sind Roadmap.

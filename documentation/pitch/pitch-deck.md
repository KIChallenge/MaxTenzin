# Pitch-Deck – SV KI-Lotse „Lotsi“ (Fachjury, 7 Minuten + Demo)

Ausführliche Fassung (Reserve für Q&A). Für den Pitch gilt die 3-Folien-Fassung `pitch-deck-minimal.md`.
Entwurf für die Folien, Deutsch. Jede Folie: **Titel · Inhalt der Folie · Sprechtext (≈ 30–40 s)**.
Zahlen vor dem Pitch gegen `make test`, `evals/REPORT.md` und `knowledge/extracted/MANIFEST.json` prüfen.
Die Live-Demo (Folie 5) folgt `documentation/demo-script.md`; bei Zeitdruck die Kurzfassung (4 Minuten).

---

## Folie 1 – Titel
**SV KI-Lotse „Lotsi“ – ein Lotse, kein Chatbot**
Untertitel: Von der ersten Frage bis zum unterschriftsreifen Antrag. Use Case 1 · Team MaxTenzin
Bild: Cockpit-Screenshot `documentation/screenshots/03-uebersicht-lebenslage-behandlungsteam.png`

> Sprechtext: „Der Use Case sagt: gesucht ist kein Chatbot, sondern ein Lotse, der von der ersten Frage bis zur Inanspruchnahme begleitet. Genau das zeigen wir – mit einer These, die uns vom ersten Tag an geleitet hat.“

## Folie 2 – Das Problem in einem Brief
**Acht Aufgaben, sechs Stellen, null Überblick**
- Anna Berger, 78, nach Spitalsentlassung: Pflegegeld · Reha · mobile Pflege · Fahrtkosten · Rezeptgebühr · Kontrolltermin · Meldepflicht · Medikationsplan
- Ihre Tochter Maria soll das organisieren – mit Vollmacht, aber ohne Fachwissen
- Heute: Formulare suchen, Angaben mehrfach machen, Zuständigkeiten raten

> Sprechtext: „Das ist der Entlassungsbrief aus den Challenge-Daten. Acht offene Aufgaben, verteilt auf PVA, ÖGK, FSW und die Hausärztin. Maria ist keine Expertin – sie ist Tochter. Der Use Case nennt genau diesen Fall: Angehörige, die Leistungen organisieren müssen.“

## Folie 3 – Unsere These
**„KI funktioniert nur gut und vor allem sicher, wenn Prozesse definiert sind. Wir bauen sie als Top Layer auf unsere anderen Services.“**
- Entscheiden tun deterministische, quellenbelegte Dienste: Anspruch, Beträge, Fristen, Zuständigkeit
- Die KI versteht, routet, extrahiert und erklärt – sie entscheidet nichts
- Sie nutzt dieselben Schnittstellen wie die Oberfläche, mit genau den Rechten der Person

> Sprechtext: „Wir haben nicht zuerst einen Chat gebaut und dann Regeln drumherum. Wir haben zuerst die Prozesse als Dienste gebaut – jeder mit Quelle – und Lotsi als oberste Schicht darauf gesetzt. Das macht ihn sicher, prüfbar und morgen austauschbar.“

## Folie 4 – So arbeitet Lotsi: keine Sonderrechte
**Frage → Lotsi → Werkzeug → Dienst (mit Annas Vollmacht) → Antwort + Quelle**
- 14 Dienste: Vertretung · Lebenslage · Dokumente · Leistungen · Anträge · Termine · Fall · Vorsorge · Rechtsgrundlagen · Werte · Medikamente · Stellen · Benachrichtigungen · Protokoll
- 31 Werkzeuge, jedes ist genau ein Dienst-Aufruf – per HTTP, mit dem Token der Person
- Jeder Aufruf im Transparenz-Protokoll: „Lotsi (KI) · Leistungen prüfen · erlaubt / verweigert“
Bild: Architekturgrafik aus `documentation/architecture.md`, Screenshot `10-transparenz.png`

> Sprechtext: „Lotsi hat keinen Datenbankzugang und keine eigenen Rechte. Fehlt Maria das Recht, Anträge vorzubereiten, kann es Lotsi auch nicht – das sehen Sie gleich live, zu Beginn der Demo, mit abgelehntem Aufruf im Protokoll.“

## Folie 5 – Live-Demo
**Maria organisiert Annas Nachsorge – in 5 Minuten**
Anna erteilt Maria per Chat die Rechte → Foto des Briefs → ausdrücklich dokumentierte Empfehlungen (Zitat + Seite) → Lebenslage übernehmen → Leistungen mit Quelle → offizielles PVA-Formular PAL 080 als Entwurf, per Chat befüllt → Meldepflicht im Posteingang → Rezeptgebühr aus der Wertetabelle → Kontrolltermin bei der Hausärztin → Mein Fall
Dann: die medizinische Grenze · Transparenz-Protokoll · Stefan auf Englisch: Gesundheit, Kind, Arzttermin

> Sprechtext: Drehbuch `documentation/demo-script.md`. Wartezeiten mit den Sätzen aus der Spalte „Was man sagt“ überbrücken.

## Folie 6 – Der Schlüsselsatz
**§ 5 BPGG sagt 157,30 € – Stand 2020. Der Werte-Dienst sagt 206,20 € – Stand 2026, mit Quelle.**
- Ein Sprachmodell aus dem Gedächtnis würde den Gesetzestext zitieren – und falsch liegen
- Beträge kommen nur aus den amtlichen Wertetabellen (veraendW), nie aus dem Modell
- Ein Prüfschritt verwirft jeden €-Betrag, den kein Dienst geliefert hat

> Sprechtext: „Das ist der Grund für unsere These in einer Zahl. Der Gesetzestext ist veraltet, die Wertetabelle nicht. Die KI darf nur sagen, was ein Dienst belegt hat. Deshalb: erst definierte Prozesse, dann KI.“

## Folie 7 – Grenzen, die man sehen kann
**Diagnose abschreiben – ja. Deuten – nie.**
- Keine Diagnosen, keine Befundinterpretation, keine Risiken, keine Therapie- oder Medikamentenratschläge – Prüfung **vor** dem Antwortmodell, Antwort in < 1 s
- Aus Dokumenten nur ausdrücklich dokumentierte Empfehlungen, jedes Zitat deterministisch gegen die Seite geprüft; Inhalte werden wörtlich wiedergegeben, nie gedeutet; ärztliche Anweisungen macht Lotsi nicht zu Aufgaben
- Nichts wird eingereicht; Zustimmungs-Häkchen setzt nur die Person; Dokument-Vorschläge gelten erst nach „Ja, übernehmen“
- Rechtsinformation immer mit Fassung und „unverbindlich, keine Rechtsberatung“

> Sprechtext: „Der Use Case zieht eine klare medizinische Grenze. Bei uns ist sie kein Prompt-Wunsch, sondern ein eigener Prüfschritt mit 20 automatisierten Grenzfällen – inklusive Prompt-Injection über ein präpariertes PDF.“

## Folie 8 – Vier Szenarien, eine Person im Mittelpunkt
**Die Szenarien des Use Case – und die Personalisierung aus Abschnitt 3**
| Szenario | Was Lotsi tut |
|---|---|
| Pflege („Meine Mutter braucht Hilfe“) | Bündel: Pflegegeld, Pflegeberatung, mobile Dienste, Angehörigenleistungen; nur 1–2 Rückfragen |
| Gesundheitsförderung | Vorsorgeuntersuchung, Impfplan vs. e-Impfpass, Bewegt im Park, Rauchfrei … mit Namen und Quelle |
| Case Manager nach Spital | Dokument → Empfehlung → Prozess → Stelle → Antrag → Unterlagen → Termin |
| Kind | Eltern-Kind-Pass, Familienbeihilfe, Kinderbetreuungsgeld, Ernährung, zuständige Stelle |
Personalisierung: Sprache (Deutsch/Englisch/Türkisch), Einfache Sprache, Detailtiefe, Spracheingabe, Termin-Vorlieben (Nähe, Tageszeit, barrierefrei), Behandlungsteam – einmal eingestellt, nie wieder gefragt. Gemeinsames Wissen: Was die Person einmal beantwortet hat, wird mit Herkunft gespeichert.

> Sprechtext: „Das sind die vier Szenarien aus dem Use Case – alle vier laufen auf denselben Diensten. Und Lotsi spricht die Sprache der Person: Englisch, Einfache Sprache, kurz oder ausführlich.“

## Folie 9 – Daten, die wir wirklich nutzen
**Alle fünf Datensätze der Challenge – bis auf einen, bewusst**
- SozDok: 1.976 Paragraphen aus 19 Gesetzen und Richtlinien, Volltextsuche, jede Fundstelle mit Fassung
- Wertetabellen 2026 (veraendW): 686 Werte, z. B. Pflegegeld, Rezeptgebühr, Richtsätze
- Erstattungskodex: 6.985 Packungen – Box, Preis, Bewilligung, „Sie zahlen …“ (rein administrativ)
- Formulare: offizielle AcroForm-PDFs direkt befüllt (PAL 080, FSW, Kur/Reha, Fahrtkosten), Ergebnis als ENTWURF
- Befunde: Entlassungsbrief, e-Impfpass, Röntgen – Zitat + Seite, Grenze bei Bildgebung
- Serviceratgeber ÖGK 2026: 118 Seiten für Stellen, Angebote, Vorsorge
- Bewusst nicht: Honorarordnung (Steiermark 2025 – falsche Region für unsere Personen)
Qualität: 262 automatische Tests · 35/35 Live-Evals (Szenarien, Grenzfälle, Vollmacht, Sprache) · jede Antwort mit Quelle

> Sprechtext: „Jede Zahl, die Sie heute gesehen haben, hat eine Quelle, die Sie anklicken können. Und wir sagen auch, was wir weglassen – und warum.“

## Folie 10 – Vom Prototyp zum Betrieb
**Jeder Demo-Baustein hat einen realen Ersatz hinter derselben Schnittstelle**
- Login & Vollmacht: ID Austria / e-Vollmacht statt Demo-Token – Token, Vertretung, Berechtigungen sind das Modell
- Gesundheitsdaten: ELGA e-Befunde und e-Impfpass-API statt Upload – dieselbe Zitatprüfung
- Träger: Übergabe an meinSV / Online-Formulare mit Klick der Person, Status zurück in „Mein Fall“; echte Terminsysteme
- Fläche: Stellen und Ordinationen aller Bundesländer (Serviceratgeber S. 96–115), SVS und BVAEB
- Offen: dieselben 31 Werkzeuge als MCP-Server – andere Assistenten nutzen die Dienste mit ID-Austria-Login und genau den erteilten Rechten
- Betrieb: Microservice-Schnitt entlang der bestehenden Grenzen, Postgres, Audit append-only, Modell-Pinning mit Evals als Release-Gate

> Sprechtext: „Weil die Prozesse Dienste sind, ist der Weg in die Produktion ein Austausch von Bausteinen, kein Neubau. Der erste Mehrwert – Angehörige füllen offizielle Formulare in Minuten statt Tagen aus – braucht nur den ID-Austria-Login.“

## Folie 11 – Warum das zählt
**Ein Lotse, der nichts erfindet, nichts einreicht und nichts darf, was die Person nicht erlaubt hat**
- Nutzen: vom Foto des Briefs zum unterschriftsreifen Antrag, mit Meldepflicht, Termin und offenen Schritten im Blick
- Verantwortung: medizinische Grenze als Prüfschritt, Quellen überall, Rechte der Person gelten auch für die KI
- Weg: definierte Prozesse zuerst – jeder neue Dienst macht Lotsi klüger, ohne die KI neu zu bauen

> Sprechtext: „Kein Chatbot. Ein Lotse auf definierten Prozessen. Danke – wir freuen uns auf Ihre Fragen.“ (Q&A-Antworten: `documentation/demo-script.md`, Abschnitt Q&A.)

---

## Abgleich mit den Bewertungskriterien der Fachjury
| Kriterium (aus dem Use Case) | Wo es im Pitch sichtbar wird |
|---|---|
| Eigenständig und durchdacht entwickelt | Folie 3–4: These, Dienste zuerst, KI als Top Layer, keine Sonderrechte |
| Flexibel und intelligent über verschiedene Aufgaben | Folie 5 + 8: Dokument, Anspruch, Antrag, Termin, Lebenslage, Kind, freie Anliegen ohne Bündel (Q&A) |
| Daten und Wissensquellen genutzt und verknüpft | Folie 6 + 9: Gesetz vs. Wertetabelle, Brief → Rezeptgebühr → EKO, Quelle an jeder Aussage |
| Verständlichkeit und Nutzerorientierung | Folie 8: Einfache Sprache, Sprachen, Detailtiefe, nur nötige Rückfragen, Behandlungsteam |
| Qualität der Unterstützungsleistungen und Handlungsschritte | Folie 5: offizielles Formular, Unterlagen, zuständige Stelle, Meldepflicht mit Frist, Termin, Mein Fall |
| Umgang mit Unsicherheit, Transparenz, fachliche Grenzen | Folie 7: Grenze vor dem Modell, Status „noch nicht beurteilbar“, Protokoll, „bitte prüfen“ bei Fotos |
| Realistische Weiterentwicklung, rascher Mehrwert | Folie 10: Austausch hinter denselben Schnittstellen, erster Nutzen mit ID Austria |
| Innovativer Zusatznutzen | Vollmacht gilt auch für die KI · Lebenslage mit Zustimmung · Chat und Assistent am selben Antrag · MCP-Option |

# Kernbotschaft & Sprechnotizen – „Ein KI-Lotse ist nur so gut wie seine Infrastruktur“

Notizen für Demo und Pitch (Deutsch). Ergänzt `pitch-deck.md`; Zahlen vor dem Pitch mit `make test` und `evals/REPORT.md` prüfen.

---

## Die Botschaft in drei Sätzen
1. **Jeder KI-Assistent ist nur so gut wie die Infrastruktur darunter.** Das Sprachmodell ist austauschbar – die Dienste, Daten und Regeln sind es nicht.
2. **Halluzinationen verhindert man nicht mit einem besseren Prompt, sondern per Design:** Die KI entscheidet nichts. Sie darf nur über definierte Schnittstellen arbeiten und nur sagen, was ein Dienst mit Quelle geliefert hat.
3. **Der eigentliche Wert – und der schwierigste Teil – ist deshalb die Infrastruktur und der richtige Kontext:** Daten aufbereiten, Regeln mit Quelle hinterlegen, Rechte durchreichen, Antworten prüfen.

Merksatz für die Folie: **„Erst die Prozesse, dann die KI.“**

## Vorsicht bei der Formulierung
- **Nicht sagen:** „Lotsi halluziniert nicht.“ – Das stimmt so nicht, und ein Jurymitglied wird es live testen.
- **Sagen:** „Lotsi entscheidet nichts. Er formuliert nur, was die Dienste entschieden haben – und diese Formulierung wird geprüft.“
- Ehrlich und stark: „Das Modell kann sich im Ausdruck irren. Deshalb prüfen wir die Antwort, bevor sie die Person sieht – Beträge, Zusagen, Quellen.“

## Wie wir Halluzinationen per Design eingrenzen (drei Schichten)
| Schicht | Was passiert | Beleg im Projekt |
|---|---|---|
| **Vorher: Grenzen** | Medizinische Fragen (Diagnose, Befund, Medikation, Prognose) werden erkannt, **bevor** das Modell antwortet | 20 Grenzfälle in den Evals, Antwort in < 0,2 s ohne Sprachmodell |
| **Währenddessen: nur Werkzeuge** | Lotsi hat keine Datenbank und kein eigenes Wissen über Ansprüche. 31 Werkzeuge, jedes genau ein Dienst-Aufruf – mit dem Login und den Rechten der Person | Ohne erteilte Berechtigung kann Lotsi es auch nicht (Demo-Start, Transparenz-Protokoll) |
| **Nachher: Prüfung der Antwort** | €-Beträge ohne Dienst-Herkunft werden verworfen; Zitate aus Dokumenten werden gegen die Seite geprüft; „eingereicht“-Behauptungen werden abgefangen; Pflichtangaben (z. B. Rezeptgebühr 7,55 € mit Quelle) werden deterministisch ergänzt | 35/35 Live-Evals, Prüfung: „jeder €-Betrag auf einen Dienst rückführbar“ |

## Warum Infrastruktur und Kontext der schwierige Teil sind (aus diesem Projekt)
- **Daten richtig machen:** 1.976 Paragraphen aus 19 Gesetzen, 686 Werte aus den Wertetabellen 2026, 6.985 Packungen aus dem Erstattungskodex, Serviceratgeber seitengenau – reproduzierbar extrahiert, jede Datei mit Herkunft (`knowledge/extracted/MANIFEST.json`).
- **Die richtige Quelle wählen:** § 5 BPGG nennt noch 157,30 € (Stand 2020). Richtig für 2026 ist 206,20 € aus der Wertetabelle. Ein Modell aus dem Gedächtnis zitiert das Gesetz – und liegt falsch. **Das ist die These in einer Zahl.**
- **Offizielle Formulare:** Wir befüllen die echten PDF-Formulare der PVA/ÖGK/FSW Feld für Feld – dafür musste jedes Formularfeld einer Angabe mit Herkunft zugeordnet werden.
- **Rechte durchreichen:** Vertretung (Maria für Anna) mit einzelnen Berechtigungen – gilt für Oberfläche und KI gleichermaßen.
- **Kontext je Anfrage:** Was die Person schon beantwortet hat, Lebenslage, Behandlungsteam, Vorlieben, Sprache – geladen über dieselben Dienste, nicht „erinnert“ vom Modell.

## Ehrliche Anekdote (gut für Q&A)
„Heute Nachmittag hat Lotsi in einer Antwort den Betrag der Rezeptgebühr weggelassen und auf Englisch ‚may is an option‘ geschrieben. Das Modell bleibt ein Sprachmodell. Der Fix war nicht ein längerer Prompt, sondern ein deterministischer Schritt: Der Betrag kommt aus der Wertetabelle und wird garantiert angezeigt. Genau so sieht ‚Infrastruktur statt Prompt‘ im Alltag aus.“

## Wo die Botschaft in der Demo sichtbar wird
| Moment in der Demo | Satz dazu |
|---|---|
| Brief hochladen → Empfehlungen mit Zitat + Seite | „Lotsi liest nur, was ausdrücklich dasteht – mit Seite. Kein Zitat, keine Aussage.“ |
| Leistungsprüfung mit Status und Quelle | „Ob ein Anspruch wahrscheinlich ist, entscheidet ein Regeldienst, nicht das Modell.“ |
| Pflegegeld-Betrag / Rezeptgebühr | „Diese Zahl kommt aus der amtlichen Wertetabelle 2026 – die Quelle steht direkt daneben.“ |
| Transparenz-Protokoll | „Jeder Schritt der KI ist ein normaler Dienst-Aufruf – sichtbar, mit Rechten, prüfbar.“ |
| Maria darf zu Beginn nicht, Anna erteilt per Chat | „Die KI hat keine Sonderrechte. Was Maria nicht darf, darf Lotsi auch nicht.“ |
| Röntgenbefund „Was bedeutet das?“ | „Die Grenze ist kein Prompt-Wunsch, sondern ein eigener Prüfschritt vor dem Modell.“ |

## Erwartbare Fragen
- **„Halluziniert das trotzdem?“** – Im Ausdruck kann sich das Modell irren; bei Entscheidungen, Beträgen und Quellen nicht, weil die nur von Diensten kommen und die Antwort geprüft wird. Die Evals messen genau das.
- **„Ist das nicht einfach ein Chatbot mit Datenbank?“** – Nein: Die Dienste sind dieselben wie für die Oberfläche, mit denselben Rechten. Die KI ist die oberste Schicht, nicht das Fundament.
- **„Was passiert mit einem besseren Modell?“** – Lotsi wird besser im Verstehen und Erklären. Die Entscheidungen bleiben gleich – das ist gewollt.
- **„Warum druckt man das Formular noch aus?“** – Im Prototyp endet es bewusst als Entwurf. Im Betrieb geht der Antrag per Schnittstelle direkt an die zuständige Stelle (z. B. meinSV, PVA-Onlineformular) – **abgeschickt wird aber immer mit dem Klick der Person, nie von Lotsi.** Status und Rückfragen der Stelle landen dann in „Mein Fall“.
- **„Was war am schwierigsten?“** – Nicht die KI, sondern die Daten und Prozesse: richtige Quelle, richtige Fassung, richtige Formularfelder, richtige Rechte.

## Offen vor dem Pitch
- Folie 9 nennt 262 Tests – aktuell sind es 260 API-Tests + 6 Extraktionstests. Vor dem Pitch mit `make test` abgleichen.
- Optional: Folie 3 und 11 auf die Kernbotschaft „nur so gut wie die Infrastruktur“ zuspitzen.

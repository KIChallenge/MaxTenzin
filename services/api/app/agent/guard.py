"""Deterministic guardrails around the model.

INPUT guard (before any LLM/tool call): medical boundary + process boundary (submit / doctor-only sections / role-play).
OUTPUT guard (after the LLM): every € amount must occur in this turn's tool results (or the user's own message);
no claims of having submitted anything; prevention wording never "Ihnen fehlt".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFC", text.lower().replace("i\u0307", "i"))
    return re.sub(r"\s+", " ", t)


# --------------------------------------------------------------------------------------------- language
_LANG_HINTS = {
    "en": r"\b(the|what|my|does|mean|please|can|you|have|how|should|is|it|help|she|he|her|his|was|which|could|"
          r"get|from|mother|father|and|to|for|of|with|according|letter|benefits?)\b",
    "tr": r"\b(ne|bir|benim|annem|için|nasıl|mı|mi|ilaç|doktor|yardım|lütfen|nedir)\b|[şğı]",
}
_DE_HINTS = r"\b(der|die|das|und|ich|meine?|bitte|ist|nicht|was|wie|für|mit|kann)\b|[äöüß]"


def detect_language(text: str, default: str = "de") -> str:
    t = _norm(text)
    de = len(re.findall(_DE_HINTS, t))
    scores = {k: len(re.findall(p, t)) for k, p in _LANG_HINTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 and scores[best] > de else default


# --------------------------------------------------------------------------------------------- boundary
@dataclass
class BoundaryHit:
    category: str
    pattern: str


# Order matters: emergencies first. Patterns are intent patterns, not disease names, so that people may still
# state facts ("Diagnose laut Entlassungsbrief: …") while filling a form.
_PATTERNS: list[tuple[str, str]] = [
    ("suicide", (r"(umbringen|suizid|selbstmord|nicht mehr leben|das leben nehmen|kill myself|suicid|"
                r"intihar|kendimi öldür)")),
    ("emergency", (r"(notfall|notarzt|keine luft|atemnot|kaum luft|brustschmerz|schmerzen in der brust|"
                  r"bewusstlos|ohnmächtig|krampfanfall|starke blutung|blutet stark|schlaganfall|herzinfarkt|"
                  r"lähmung|gesicht hängt|vergiftung|emergency|can'?t breathe|chest pain|unconscious|acil durum|"
                  r"nefes alamıyor)")),
    ("role_play", (r"(du bist (jetzt |ab jetzt )?(dr\.?|doktor) |dr\.? house|tu so,? als (ob )?(du|wärst)|stell dir vor,? du (bist|wärst)|du bist (jetzt )?(ein|eine|mein|"
                  r"meine) ?(arzt|ärztin|doktor|onkolog|radiolog)|als (arzt|ärztin|doktor) (antworten|sprechen|"
                  r"beurteilen)|antworte (wie|als) (ein |eine )?(arzt|ärztin)|pretend (to be|you are) a doctor|"
                  r"act as a doctor|doktor gibi davran)")),
    ("doctor_section", (r"((arzt|ärzt|medizinisch)\w*\s*(teil|abschnitt|bereich|stellungnahme|gutachten|befundbericht)"
                       r"[^.?!]{0,40}(aus|füll|ergänz|schreib|übernehm)|"
                       r"(füll|ergänz|schreib|übernimm|mach)\w*[^.?!]{0,40}(ärztlich|arztteil|arzt-teil|"
                       r"ärzteteil|medizinischen teil|stellungnahme des arztes)|fill (in|out) the doctor)")),
    ("submit", (r"((reich|schick|send|übermittel|stell)\w*[^.?!]{0,40}\w*(antrag|anträge|formular|ansuchen)\b[^.?!]{0,30}"
               r"\b(ein|ab|weg|für mich|direkt)\b|\b(antrag|anträge|formular)\b[^.?!]{0,40}\b(einreichen|abschicken|"
               r"absenden|übermitteln|abgeben)\b|submit (the|my) (application|form)|başvuruyu gönder)")),
    ("diagnosis", (r"(was (habe|hab|hat) (ich|sie|er|meine mutter|mein vater|mein kind)\b[^.?!]{0,30}\?|"
                  r"(stell|stelle|gib|mach)\w*[^.?!]{0,20}diagnose|welche (krankheit|erkrankung|diagnose) "
                  r"(habe|hat|könnte)|habe ich (wohl |vielleicht |etwa )?(krebs|einen tumor|corona|covid|diabetes)|"
                  r"(ist|sind) (das|es|der knoten|die werte)\b[^.?!]{0,35}(krebs|bösartig|gutartig|gefährlich|schlimm|"
                  r"ernst)|könnte (das|es) (krebs|ein tumor|bösartig)|what do i have|diagnose me|teşhis)")),
    ("findings", (r"((was|wie) (bedeutet|heißt|heisst|sagt|zeigt)\w*[^.?!]{0,60}(befund|röntgen|mrt|ct|ultraschall|"
                 r"laborwert|blutwert|werte\b|aufnahme|histolog|befundergebnis)|"
                 r"(befund|röntgen\w*|mrt|laborwerte?|blutwerte?)[^.?!]{0,40}(erklär|deut|interpretier|"
                 r"übersetz|bewert|beurteil|verständlich)|(erklär|deut|interpretier|bewert|beurteil)\w*[^.?!]{0,40}"
                 r"(befund|röntgen|mrt|laborwert|blutwert|werte)|is (my|the) (result|report|x-?ray|scan) "
                 r"(bad|normal|serious)|what do(es)? (my|the) [^?.]{0,30}(report|result|x-?ray|scan|finding)s? mean|"
                 r"explain (my|the) [^?.]{0,30}(report|result|finding|x-?ray|scan)|sonuç(lar)?ım ne anlama)")),
    ("prognosis", (r"(prognose|heilungschance|überlebens(chance|rate|zeit)|wie lange (habe|hat|bleibt)\w*[^.?!]{0,30}"
                  r"(zu leben|noch)|lebenserwartung|wird (sie|er|ich|meine mutter|mein vater) wieder gesund|"
                  r"(wie hoch|wie groß|wie gross) ist (das|mein|ihr|sein) risiko|risiko[^.?!]{0,30}(rückfall|"
                  r"metastase|krebs|sterben|tod)|rückfallrisiko|how long (do|does) .* (live|have left)|prognosis)")),
    ("medication", (r"(wie ?viel\w* (mg|milligramm|tabletten|tropfen|pillen|einheiten|hub)|"
                   r"(absetzen|abzusetzen|weglassen|dosis|dosier\w*|überdosis|halbieren|"
                   r"verdoppeln|erhöhen)[^.?!]{0,40}\b(medikament\w*|tablette\w*|mg|tropfen|pille\w*|"
                   r"chemo\w*|antibiotik\w*|schmerzmittel|cortison|kortison|insulin)\b|"
                   r"\b(medikament\w*|tablette\w*|mg|pille\w*|chemo\w*|schmerzmittel|cortison|kortison|insulin)\b"
                   r"[^.?!]{0,40}(absetzen|weglassen|dosier\w*|wie viel|wieviel|wie oft|nehmen soll|"
                   r"halbieren|verdoppeln|erhöhen|vertragen)|welches? (medikament|schmerzmittel|therapie|"
                   r"behandlung)[^.?!]{0,30}(soll|sollte|empfiehlst|empfehlen|besser|helfen)|"
                   r"(soll|sollte|darf|muss) (ich|sie|er|meine mutter)[^.?!]{0,30}(medikament\w*|tablette\w*|pille\w*)"
                   r"[^.?!]{0,20}(nehmen|einnehmen|weiter)|"
                   r"(soll|sollte) (ich|sie|er|meine mutter)[^.?!]{0,40}(therapie|behandlung|bestrahlung|chemo|"
                   r"operation)[^.?!]{0,30}(machen|abbrechen|ablehnen|beginnen)|"
                   r"(stop|stopp|reduce|double) (taking )?(my|the) (medication|pills|dose)|how much .* should i take|"
                   r"ilacı bırak|ilaç dozu)")),
]
_COMPILED = [(c, re.compile(p)) for c, p in _PATTERNS]

# Health-related vocabulary: only these messages go to the (optional) small LLM double-check.
HEALTH_TERMS = re.compile(r"(befund|diagnos|tumor|krebs|karzinom|metasta|röntgen|mrt\b|\bct\b|blutwert|laborwert|"
                          r"medikament|tablette|dosis|therapie|chemo|bestrahlung|schmerz|symptom|krank|arzt|ärztin|"
                          r"doctor|medication|diagnos|x-?ray)")


def check_boundary(message: str) -> BoundaryHit | None:
    t = _norm(message)
    for cat, rx in _COMPILED:
        m = rx.search(t)
        if m:
            return BoundaryHit(cat, m.group(0))
    return None


_REDIRECT_DE = ("Gerne helfe ich Ihnen stattdessen, einen Termin bei Ihrer Hausärztin bzw. Ihrem Hausarzt "
                "vorzubereiten, die zuständige Stelle zu finden oder Fragen für das Arztgespräch zu notieren.")
TEMPLATES_DE = {
    "suicide": ("Es tut mir leid, dass es Ihnen gerade so schlecht geht. Sie sind damit nicht allein. Bitte wenden Sie "
                "sich sofort an die **Telefonseelsorge 142** (rund um die Uhr, kostenlos) oder bei akuter Gefahr an den "
                "**Notruf 144**. Ich bin ein Lotse für Sozialversicherungsfragen und kann in dieser Situation nicht "
                "ausreichend helfen – Menschen am Telefon schon."),
    "emergency": ("Das klingt nach einem möglichen Notfall. Bitte rufen Sie **sofort den Notruf 144** an. Wenn Sie "
                  "unsicher sind, wie dringend es ist, erreichen Sie die **Gesundheitsberatung 1450** rund um die Uhr. "
                  "Ich kann medizinische Situationen nicht einschätzen."),
    "diagnosis": ("Eine Diagnose kann und darf ich nicht stellen – das kann nur eine Ärztin bzw. ein Arzt nach einer "
                  "Untersuchung. " + _REDIRECT_DE + " Bei akuten Beschwerden: Gesundheitsberatung 1450."),
    "findings": ("Ich interpretiere keine medizinischen Befunde und bewerte keine Ergebnisse – das gehört in das "
                 "Gespräch mit der Ärztin bzw. dem Arzt, die den Befund angefordert haben. Ich kann Ihnen aber helfen, "
                 "den Befund für das Gespräch bereitzulegen, Fragen dafür zu notieren und einen Termin oder die "
                 "zuständige Stelle zu finden."),
    "prognosis": ("Zu Prognosen, Risiken oder Heilungschancen kann ich nichts sagen – das kann nur das behandelnde "
                  "Team mit Kenntnis aller Befunde einschätzen. " + _REDIRECT_DE),
    "medication": ("Zu Medikamenten, Dosierungen oder Therapien gebe ich keine Empfehlungen. Bitte ändern oder setzen "
                   "Sie nichts ab, ohne mit Ihrer Ärztin bzw. Ihrem Arzt oder Ihrer Apotheke zu sprechen. Was ich tun "
                   "kann: administrative Fragen klären, z. B. Rezeptgebühr, Kostenübernahme oder Bewilligungspflicht "
                   "laut Erstattungskodex."),
    "doctor_section": ("Den ärztlichen Teil eines Antrags (z. B. die „Ärztliche Stellungnahme“) fülle ich nicht aus – "
                       "diesen Abschnitt darf nur die Ärztin bzw. der Arzt ausfüllen. Ich bereite gerne alle Teile vor, "
                       "die Sie selbst ausfüllen dürfen, und sage Ihnen, wem Sie das Formular für den ärztlichen Teil "
                       "geben."),
    "submit": ("Ich reiche nichts für Sie ein – das ist bewusst so. Ich bereite den Antrag als **Entwurf** vor; Sie "
               "prüfen ihn, unterschreiben und schicken ihn selbst an die zuständige Stelle. Gerne erstelle ich den "
               "PDF-Entwurf und sage Ihnen, wohin er geschickt wird."),
    "role_play": ("Ich kann nicht in die Rolle einer Ärztin oder eines Arztes schlüpfen – auch nicht spielerisch. Ich "
                  "bin Ihr Lotse für Leistungen, Anträge und Zuständigkeiten der Sozialversicherung. " + _REDIRECT_DE),
}
TEMPLATES_EN = {
    "suicide": "I'm sorry you are going through this. Please call the Austrian crisis line **Telefonseelsorge 142** "
               "(24/7, free) or **emergency 144** right now.",
    "emergency": "This sounds like a possible emergency. Please call **144** immediately. If unsure, call the health "
                 "hotline **1450** (24/7). I cannot assess medical situations.",
    "default": "I can't give diagnoses, interpret medical findings, assess risks or advise on medication or therapy – "
               "please discuss this with your doctor. I'm happy to help you prepare the appointment, find the "
               "responsible office or prepare an application draft (which you review, sign and send yourself).",
}
TEMPLATES_TR = {
    "suicide": "Lütfen hemen **Telefonseelsorge 142** (7/24, ücretsiz) veya acil durumda **144** numarasını arayın.",
    "emergency": "Bu acil bir durum olabilir. Lütfen hemen **144**'ü arayın. Emin değilseniz **1450** sağlık hattını "
                 "arayın.",
    "default": "Teşhis koyamam, tıbbi bulguları yorumlayamam ve ilaç ya da tedavi önerisinde bulunamam – lütfen "
               "doktorunuzla konuşun. Randevu hazırlığında, yetkili kurumu bulmada veya başvuru taslağında "
               "yardımcı olabilirim.",
}
SUGGESTIONS = {
    "suicide": ["Telefonseelsorge 142 anrufen", "Notruf 144"],
    "emergency": ["Notruf 144", "Gesundheitsberatung 1450"],
    "doctor_section": ["Meine Teile des Antrags vorbereiten", "Wem gebe ich das Formular?"],
    "submit": ["PDF-Entwurf erstellen", "Wohin schicke ich den Antrag?"],
    "medication": ["Rezeptgebühr prüfen", "Termin bei der Hausärztin vorbereiten"],
}
DEFAULT_SUGGESTIONS = ["Termin bei der Hausärztin vorbereiten", "Zuständige Stelle finden", "Fragen fürs Arztgespräch notieren"]


def boundary_reply(category: str, lang: str = "de") -> tuple[str, list[str]]:
    if lang == "en":
        return TEMPLATES_EN.get(category, TEMPLATES_EN["default"]), SUGGESTIONS.get(category, DEFAULT_SUGGESTIONS)
    if lang == "tr":
        return TEMPLATES_TR.get(category, TEMPLATES_TR["default"]), SUGGESTIONS.get(category, DEFAULT_SUGGESTIONS)
    return TEMPLATES_DE[category], SUGGESTIONS.get(category, DEFAULT_SUGGESTIONS)


LLM_BOUNDARY_SYSTEM = (
    "Du bist ein Klassifikator. Entscheide, ob die Nutzernachricht von einem Sozialversicherungs-Lotsen eine "
    "medizinische Bewertung verlangt. Kategorien: diagnosis (Diagnose stellen), findings (Befund/Werte deuten), "
    "prognosis (Prognose/Risiko), medication (Medikament/Dosis/Therapie-Rat), emergency (akuter Notfall), none. "
    "Administrative Fragen (Kosten, Rezeptgebühr, Anträge, Zuständigkeit, was im Dokument ausdrücklich empfohlen wird) "
    "sind none. Antworte als JSON: {\"category\": \"...\"}"
)


# --------------------------------------------------------------------------------------------- output guard
_NUM = r"\d{1,3}(?:[.\s ]\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?"
_AMOUNT_RX = re.compile(rf"(?:€|eur\b|euro\b)\s*({_NUM})|({_NUM})\s*(?:€|eur\b|euro\b)", re.IGNORECASE)
_ANY_NUM_RX = re.compile(r"\d+(?:[.,]\d+)*")


def parse_number(s: str) -> float | None:
    s = s.strip().replace(" ", "").replace(" ", "").replace("\xa0", "")
    try:
        if "," in s:
            return round(float(s.replace(".", "").replace(",", ".")), 2)
        if "." in s and len(s.split(".")[-1]) == 3:
            return round(float(s.replace(".", "")), 2)
        return round(float(s), 2)
    except ValueError:
        return None


def amounts_in_text(text: str) -> list[float]:
    out = []
    for m in _AMOUNT_RX.finditer(text):
        v = parse_number(m.group(1) or m.group(2))
        if v is not None:
            out.append(v)
    return out


def numbers_in(obj: Any, out: set[float] | None = None) -> set[float]:
    out = set() if out is None else out
    if isinstance(obj, bool):
        return out
    if isinstance(obj, int | float):
        out.add(round(float(obj), 2))
    elif isinstance(obj, str):
        for m in _ANY_NUM_RX.finditer(obj):
            v = parse_number(m.group(0))
            if v is not None:
                out.add(v)
    elif isinstance(obj, dict):
        for v in obj.values():
            numbers_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            numbers_in(v, out)
    return out


_SUBMIT_CLAIM = re.compile(r"\b(ich habe|habe ich|wurde|ist)\b[^.!?\n]{0,50}\b(eingereicht|abgeschickt|übermittelt|"
                           r"versendet)\b", re.IGNORECASE)
_MISSING_WORDING = re.compile(r"\b(ihnen|dir|ihm|ihr) fehl(t|en)\b|\bfehlende impfung", re.IGNORECASE)


def output_violations(reply: str, allowed_numbers: set[float]) -> list[str]:
    problems = []
    bad = sorted({a for a in amounts_in_text(reply) if a not in allowed_numbers})
    if bad:
        problems.append("Beträge ohne Tool-Quelle: " + ", ".join(f"{b:.2f} €" for b in bad))
    for m in _SUBMIT_CLAIM.finditer(reply):
        if "nicht" not in m.group(0).lower() and "nie" not in m.group(0).lower().split():
            problems.append("Behauptung einer Einreichung: " + m.group(0))
            break
    if _MISSING_WORDING.search(reply):
        problems.append("Formulierung 'fehlt' bei Vorsorge – verwende 'laut Impfplan empfohlen' bzw. "
                        "'nicht im e-Impfpass dokumentiert'")
    return problems

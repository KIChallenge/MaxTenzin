# 0003 Fill the official form PDFs directly (D3)
**Context:** All 7 official form PDFs in the data are AcroForms. A self-made layout would look unofficial and could drift from the Träger's current version.

**Decision:** Form schemas (`knowledge/forms/*.yaml`) map each field to its AcroForm name and export states; `forms/pdf.py` fills the official template with pypdf, keeps it editable (`NeedAppearances`), and stamps every page "ENTWURF – bitte prüfen und selbst unterschreiben". Doctor-only pages are never written.

**Consequence:** The person gets the document the Träger expects. Tests check that every mapped field and radio state exists in the PDF. 4 of 7 templates are mapped; the others are info only.

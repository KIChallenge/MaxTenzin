"""Extract the ÖGK Serviceratgeber 2026 (two A5 pages per PDF sheet) into one row per *printed* page.

PDF sheet n carries printed pages 2n-2 (left half) and 2n-1 (right half); verified against the running headers.
Text fragments are split into halves by their x-coordinate.
"""

from __future__ import annotations

import re

from pypdf import PdfReader

from common import OUT_DIR, RAW_DIR, record, write_jsonl

FILE = "Leistungskataloge/Serviceratgeber-2026_Broschuere_A5_OEAM_99-19_klein_korr.pdf"
SOURCE_LABEL = "ÖGK Serviceratgeber 2026 (Stand 01.01.2026)"


def split_page(page) -> tuple[str, str]:
    width = float(page.mediabox.width)
    left: list[str] = []
    right: list[str] = []

    def visitor(text, cm, tm, font_dict, font_size):
        if not text:
            return
        x = tm[4] * cm[0] + cm[4]  # user-space x of the fragment
        (left if x < width / 2 else right).append(text)

    page.extract_text(visitor_text=visitor)
    return "".join(left), "".join(right)


def clean(text: str) -> str:
    text = re.sub(r"-\n(?=[a-zäöüß])", "", text)  # re-join hyphenated words
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(ln.strip() for ln in text.splitlines() if ln.strip())


def main() -> None:
    path = RAW_DIR / FILE
    reader = PdfReader(str(path))
    rows = []
    for i, page in enumerate(reader.pages, start=1):
        left, right = split_page(page)
        for printed, txt in ((2 * i - 2, left), (2 * i - 1, right)):
            txt = clean(txt)
            if not txt:
                continue
            rows.append(
                {
                    "printed_page": printed,
                    "pdf_page": i,
                    "text": txt,
                    "source": f"{SOURCE_LABEL}, S. {printed}",
                }
            )
    out = OUT_DIR / "serviceratgeber" / "pages.jsonl"
    write_jsonl(out, rows)
    record("serviceratgeber_pages", sources=[path], outputs=[out], rows=len(rows),
           notes="printed page = 2*pdf_page-2 (left) / 2*pdf_page-1 (right)")
    print(f"serviceratgeber: {len(rows)} printed pages -> {out}")


if __name__ == "__main__":
    main()

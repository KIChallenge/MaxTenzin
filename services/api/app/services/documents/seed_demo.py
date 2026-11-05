"""Explicit demo seeding: copy the fictional demo PDFs from RAW_DATA_DIR/Befunde into var/uploads under their
golden demo ids and import Stefan's e-Impfpass. Never commits anything; var/ is gitignored.

    cd services/api && RAW_DATA_DIR=/path/to/docs uv run python -m app.services.documents.seed_demo
"""

from __future__ import annotations

from app.contracts.documents import DocumentSummary
from app.core.config import get_settings
from app.core.db import now_iso, store
from app.services.documents import goldens, storage
from app.services.documents.extract import analyze_pdf
from app.services.documents.pdf import detect_doc_type, page_texts, sha256
from app.services.prevention.impfpass import parse_impfpass
from app.services.prevention.router import VACCINATIONS


def seed() -> list[str]:
    befunde = get_settings().raw_data_dir / "Befunde"
    seeded = []
    for g in goldens.all_goldens():
        src = befunde / g["source_filename"]
        if not src.exists():
            continue
        data = src.read_bytes()
        if sha256(data) != g["sha256"]:
            print(f"skip {src.name}: content differs from golden")
            continue
        doc_id, subject = g["demo_document_id"], g["demo_subject_id"]
        pages = page_texts(data)
        doc_type = detect_doc_type(pages, src.name)
        storage.save_pdf(doc_id, data)
        summary = DocumentSummary(document_id=doc_id, filename=src.name, doc_type=doc_type,
                                  uploaded_at=now_iso(), owner_id=subject)
        store.put(storage.DOCS, doc_id, {**summary.model_dump(), "sha256": g["sha256"], "pages": len(pages)},
                  subject_id=subject)
        analysis = analyze_pdf(doc_id, src.name, g["sha256"], doc_type, pages)
        store.put(storage.ANALYSES, doc_id, analysis.model_dump(mode="json"), subject_id=subject)
        if "vaccinations" in g:
            store.put(VACCINATIONS, subject, {
                "subject_id": subject, "source_document_id": doc_id, "imported_at": now_iso(),
                "vaccinations": [v.model_dump() for v in parse_impfpass(pages)],
            }, subject_id=subject)
        seeded.append(f"{doc_id} ({subject}, {doc_type.value}, {len(analysis.recommendations)} recs)")
    return seeded


if __name__ == "__main__":
    for line in seed() or ["nothing seeded — RAW_DATA_DIR/Befunde not found"]:
        print(line)

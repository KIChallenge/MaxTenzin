"""Fill the OFFICIAL AcroForm PDF with pypdf and stamp it as a draft. Never submitted, never flattened."""

from __future__ import annotations

import io
import logging
from functools import lru_cache

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

from app.contracts.forms import FieldType, FieldValue
from app.services.forms.spec import FieldSpec, FormSpec, template_pdf

DRAFT_STAMP = "ENTWURF – bitte prüfen und selbst unterschreiben"

logging.getLogger("pypdf").setLevel(logging.ERROR)  # "No fields to update on this page" for info pages


@lru_cache
def field_pages(form_id: str) -> dict[str, set[int]]:
    """Fully qualified AcroForm field name -> 1-based pages carrying one of its widgets."""
    out: dict[str, set[int]] = {}
    for pi, page in enumerate(PdfReader(template_pdf(form_id)).pages, start=1):
        for annot in page.get("/Annots") or []:
            a = annot.get_object()
            if a.get("/Subtype") != "/Widget":
                continue
            parts, node = [], a
            while node is not None:
                if node.get("/T") is not None:
                    parts.append(str(node["/T"]))
                parent = node.get("/Parent")
                node = parent.get_object() if parent is not None else None
            if parts:
                out.setdefault(".".join(reversed(parts)), set()).add(pi)
    return out


def doctor_only_pdf_fields(spec: FormSpec) -> set[str]:
    """AcroForm fields whose widgets lie ONLY on doctor-only pages (shared header fields such as VSNR stay writable)."""
    if not spec.doctor_only_pages:
        return set()
    pages = set(spec.doctor_only_pages)
    return {name for name, on in field_pages(spec.form_id).items() if on <= pages}


def _split_lines(text: str, first: int, rest: int | None, n_lines: int) -> list[str]:
    """Greedy word wrap into n_lines; the last line takes whatever remains."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        limit = first if not lines else (rest or first)
        if cur and len(cur) + 1 + len(w) > limit and len(lines) < n_lines - 1:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return lines + [""] * (n_lines - len(lines))


def pdf_values(spec: FormSpec, values: dict[str, FieldValue]) -> dict[str, str]:
    """Session values -> {AcroForm name: value/export state}. Doctor-only fields are dropped defensively."""
    blocked = doctor_only_pdf_fields(spec)
    out: dict[str, str] = {}
    for f in spec.fields:
        target = f.pdf_target
        fv = values.get(f.id)
        if not target or f.doctor_only or target in blocked or fv is None or fv.value in (None, ""):
            continue
        out.update(_field_to_pdf(f, fv.value))
    return {k: v for k, v in out.items() if k not in blocked}


def _field_to_pdf(f: FieldSpec, value) -> dict[str, str]:
    target = f.pdf_target
    if f.type == FieldType.checkbox:
        return {target: f.pdf_on_value} if value is True else {}
    if f.type == FieldType.choice:
        state = f.pdf_options.get(str(value))
        return {target: state} if state else {}
    text = str(value)
    if f.pdf_overflow:
        names = [target, *f.pdf_overflow]
        lines = _split_lines(text, f.max_chars or 90, f.max_chars, len(names))
        return {n: line for n, line in zip(names, lines, strict=True) if line}
    return {target: text}


def _stamp_page(width: float, height: float, position: str) -> PdfReader:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    c.setFillColor(Color(0.8, 0.05, 0.05, alpha=0.85))
    c.setFont("Helvetica-Bold", 10)
    y = height - 14 if position == "top" else 6
    c.drawCentredString(width / 2, y, DRAFT_STAMP)
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def render_pdf(spec: FormSpec, values: dict[str, FieldValue]) -> bytes:
    reader = PdfReader(template_pdf(spec.form_id))
    writer = PdfWriter(clone_from=reader)
    fill = pdf_values(spec, values)
    for page in writer.pages:
        if page.get("/Annots"):
            writer.update_page_form_field_values(page, fill, auto_regenerate=False)
    writer.set_need_appearances_writer(True)
    for page in writer.pages:
        box = page.mediabox
        page.merge_page(_stamp_page(float(box.width), float(box.height), spec.stamp).pages[0])
    writer.add_metadata({"/Title": f"{spec.title_de} – ENTWURF", "/Subject": DRAFT_STAMP})
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def read_back(pdf: bytes) -> dict[str, str | None]:
    """AcroForm values of a rendered PDF (used by tests and the review step)."""
    fields = PdfReader(io.BytesIO(pdf)).get_fields() or {}
    return {k: (str(v.get("/V")) if v.get("/V") is not None else None) for k, v in fields.items()}

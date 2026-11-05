"""Photos of documents: file-type sniffing, image preparation and verbatim transcription (one LLM call per image).

The transcript replaces the PDF text layer; everything after it (doc type, extraction, quote verification,
medical boundary, admin facts, cache) is the unchanged PDF pipeline. Quote verification is therefore only as
good as the transcription: it proves the quote is in what the model read, not in the paper itself.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel

from app.contracts.documents import DocumentAnalysis
from app.core.db import store
from app.core.llm import get_llm

log = logging.getLogger(__name__)

PROMPT = (Path(__file__).parent / "prompts" / "vision_transcribe_de.md").read_text(encoding="utf-8")
CACHE = "vision_cache"        # live transcription per (prompt version, image sha256): same photo -> same text
TRANSCRIPTS = "document_transcripts"  # DocumentTranscript per document id (image uploads only)

PDF, JPEG, PNG, HEIC = "application/pdf", "image/jpeg", "image/png", "image/heic"
IMAGE_TYPES = {JPEG: "jpg", PNG: "png"}
MAX_IMAGES = 10
MAX_PIXELS = 60_000_000       # decompression-bomb guard (a 48 MP phone photo still passes)
MODEL_LONG_SIDE = 2048        # images are downscaled to this before sending
LOW_RES_LONG_SIDE = 1400      # below this the text is often too small to read reliably
UNREADABLE = "[unleserlich]"

PHOTO_NOTICE_DE = " Aus einem Foto gelesen – bitte prüfen Sie die übernommenen Angaben."
LOW_RES_NOTICE_DE = (" Das Foto hat eine geringe Auflösung – einzelne Angaben können fehlen oder falsch gelesen sein. "
                     "Ein schärferes, gerade aufgenommenes Foto liefert bessere Ergebnisse.")
UNSUPPORTED_DE = "Bitte laden Sie eine PDF-Datei oder ein Foto (JPG oder PNG) hoch."
HEIC_DE = ("HEIC-Fotos (iPhone-Standardformat) kann ich nicht lesen. Bitte speichern bzw. teilen Sie das Foto als "
           "JPG oder PNG (iPhone: Einstellungen › Kamera › Formate › „Maximale Kompatibilität“).")


def media_type(data: bytes) -> str | None:
    """Sniff the real type from the bytes; the client's content type / extension is not trusted."""
    if data.startswith(b"%PDF"):
        return PDF
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1", b"avif"):
        return HEIC
    return None


def image_sha(images: list[bytes]) -> str:
    """Content hash of an image upload: the plain sha256 for one photo, a hash over the page hashes for several."""
    hashes = [hashlib.sha256(b).hexdigest() for b in images]
    return hashes[0] if len(hashes) == 1 else hashlib.sha256("\n".join(hashes).encode()).hexdigest()


def open_image(data: bytes) -> Image.Image:
    """Decode and upright (EXIF orientation) an image. Raises ValueError if it is not a readable image."""
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > MAX_PIXELS:
            raise ValueError("image too large")
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise ValueError(str(e)) from e
    return ImageOps.exif_transpose(img)


def model_jpeg(data: bytes) -> tuple[bytes, int]:
    """JPEG sent to the model (upright, RGB, long side <= MODEL_LONG_SIDE) and the original long side in px."""
    img = open_image(data)
    long_side = max(img.size)
    if long_side > MODEL_LONG_SIDE:
        img.thumbnail((MODEL_LONG_SIDE, MODEL_LONG_SIDE))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=88)
    return buf.getvalue(), long_side


class TranscriptPage(BaseModel):
    page: int
    text: str
    unreadable: int = 0            # number of [unleserlich] markers
    low_resolution: bool = False


class DocumentTranscript(BaseModel):
    """What was read from the document, per page — so the user can check the basis of every quote."""
    document_id: str
    source: str                    # image | pdf
    mode: str                      # vision | vision-cached | fake | error | pdf-text
    pages: list[TranscriptPage]
    notice_de: str = ""


def _cache_key(sha: str) -> str:
    return hashlib.sha256(PROMPT.encode()).hexdigest()[:12] + ":" + sha


def _clean(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):     # tolerate a stray code fence despite the prompt
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip("\n")


def _transcribe_one(data: bytes) -> tuple[str, bool, bool]:
    """(text, low_resolution, from_cache). Live LLM call unless this exact photo was read before."""
    jpeg, long_side = model_jpeg(data)
    low_res = long_side < LOW_RES_LONG_SIDE
    key = _cache_key(hashlib.sha256(data).hexdigest())
    if (hit := store.get(CACHE, key)) is not None:
        return hit["text"], low_res, True
    url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    msg = get_llm().chat([
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": [
            {"type": "text", "text": "Schreibe den Text dieser Seite wörtlich ab."},
            {"type": "image_url", "image_url": {"url": url, "detail": "high"}},
        ]},
    ], reasoning_effort="low", max_tokens=8000)
    text = _clean(msg.content or "")
    store.put(CACHE, key, {"text": text})
    return text, low_res, False


def transcribe(document_id: str, images: list[bytes]) -> DocumentTranscript:
    """One page per image. Offline (no key): deterministic empty pages, mode "fake". Errors: mode "error"."""
    if not get_llm().live:
        pages = [TranscriptPage(page=i, text="", low_resolution=_low_res(b)) for i, b in enumerate(images, 1)]
        return DocumentTranscript(document_id=document_id, source="image", mode="fake", pages=pages,
                                  notice_de="Offline-Modus: Fotos werden ohne Sprachmodell nicht gelesen.")
    try:
        with ThreadPoolExecutor(max_workers=min(4, len(images))) as pool:
            results = list(pool.map(_transcribe_one, images))
    except Exception as e:  # noqa: BLE001 — network / auth / provider errors
        log.warning("vision transcription failed for %s: %s", document_id, e)
        pages = [TranscriptPage(page=i, text="") for i in range(1, len(images) + 1)]
        return DocumentTranscript(document_id=document_id, source="image", mode="error", pages=pages,
                                  notice_de="Das Foto konnte gerade nicht gelesen werden.")
    pages = [TranscriptPage(page=i, text=t, unreadable=t.count(UNREADABLE), low_resolution=lr)
             for i, (t, lr, _) in enumerate(results, 1)]
    mode = "vision-cached" if all(c for _, _, c in results) else "vision"
    return DocumentTranscript(document_id=document_id, source="image", mode=mode, pages=pages,
                              notice_de=_notice(pages).strip())


def _low_res(data: bytes) -> bool:
    try:
        return max(open_image(data).size) < LOW_RES_LONG_SIDE
    except ValueError:
        return False


def _notice(pages: list[TranscriptPage]) -> str:
    return PHOTO_NOTICE_DE + (LOW_RES_NOTICE_DE if any(p.low_resolution for p in pages) else "")


def mark_vision(analysis: DocumentAnalysis, transcript: DocumentTranscript) -> DocumentAnalysis:
    """Label an analysis built from a photo transcript: mode vision/vision-cached and the photo notice."""
    mode = {"live": "vision", "live-cached": "vision-cached"}.get(analysis.extraction_mode, analysis.extraction_mode)
    notice = analysis.notice_de
    if PHOTO_NOTICE_DE.strip() not in notice:
        notice += _notice(transcript.pages)
    return analysis.model_copy(update={"extraction_mode": mode, "notice_de": notice})

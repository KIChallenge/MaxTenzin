"""Live check (not a unit test): render PDF pages to JPG, upload them as photos, analyse, print the result.

    cd services/api && uv run python -m app.services.documents.live_check_vision \
        /path/to/docs/Befunde/Entlassungsbefund.pdf --pages 1 6 --dpi 150

Needs ghostscript (`gs`) and a live LLM key in .env. Rendered images go to var/vision_check/ (gitignored);
the real document is never copied into the repo. `--skew 4` rotates the pages by 4° to imitate a hand-held photo.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import time

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import app


def render(pdf: str, pages: list[int], dpi: int, skew: float, quality: int) -> list[bytes]:
    out = get_settings().var_dir / "vision_check"
    out.mkdir(parents=True, exist_ok=True)
    images = []
    for p in pages:
        path = out / f"page{p}-{dpi}dpi.jpg"
        subprocess.run(["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=jpeg", f"-r{dpi}",
                        f"-dJPEGQ={quality}", f"-dFirstPage={p}", f"-dLastPage={p}", f"-sOutputFile={path}", pdf],
                       check=True)
        img = Image.open(path)
        if skew:
            img = img.convert("RGB").rotate(skew, expand=True, fillcolor=(235, 230, 220))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=quality)
        images.append(buf.getvalue())
        print(f"  page {p}: {img.size[0]}x{img.size[1]} px, {len(buf.getvalue()) // 1024} KB")
    return images


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--pages", type=int, nargs="+", default=[1, 6])
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--skew", type=float, default=0.0)
    ap.add_argument("--quality", type=int, default=85)
    args = ap.parse_args()

    print(f"render {args.pages} @ {args.dpi} dpi, skew {args.skew}°")
    images = render(args.pdf, args.pages, args.dpi, args.skew, args.quality)
    c = TestClient(app)
    h = {"Authorization": "Bearer demo-maria", "X-Subject-Id": "anna", "X-Via": "ui"}
    t0 = time.perf_counter()
    r = c.post("/api/documents", headers=h,
               files=[("files", (f"seite{p}.jpg", b, "image/jpeg")) for p, b in zip(args.pages, images, strict=True)])
    r.raise_for_status()
    doc = r.json()
    t1 = time.perf_counter()
    a = c.post(f"/api/documents/{doc['document_id']}/analyze", headers=h).json()
    t2 = time.perf_counter()
    t = c.get(f"/api/documents/{doc['document_id']}/transcript", headers=h).json()

    print(f"\nupload+transcription {t1 - t0:.1f} s · analyze {t2 - t1:.1f} s · doc_type {doc['doc_type']}")
    print(f"transcript mode {t['mode']} · chars/page {[len(p['text']) for p in t['pages']]} · "
          f"[unleserlich] {[p['unreadable'] for p in t['pages']]} · low-res {[p['low_resolution'] for p in t['pages']]}")
    print(f"extraction_mode {a['extraction_mode']} · recommendations {len(a['recommendations'])} · "
          f"dropped_unverified {a['dropped_unverified']} · open_tasks {len(a['open_tasks'])}")
    print("notice:", a["notice_de"])
    print("\nfacts:")
    for f in a["facts"]:
        print(f"  {f['key']}: {f['value']}  (S. {f['page']})")
    print("\nrecommendations (photo page index):")
    for rec in a["recommendations"]:
        print(f"  [{rec['category']}] S.{rec['page']} {rec['related_benefit_ids']} — {rec['quote'][:110]}")


if __name__ == "__main__":
    main()

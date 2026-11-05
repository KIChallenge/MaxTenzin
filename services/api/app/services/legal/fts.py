"""SQLite FTS5 index over paragraphs.jsonl, built on first use under var/ (gitignored), BM25-ranked.

The index is rebuilt automatically when the corpus file changes (size + mtime fingerprint). Core laws for the
demo scenarios get a mild score boost so that e.g. "Pflegegeld" ranks BPGG above incidental ASVG mentions.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from pathlib import Path

from app.core.config import get_settings
from app.core.knowledge import kpath
from app.services.legal.service import CORPUS, rows

INDEX_NAME = "legal_fts.db"
LAW_BOOST = {
    "BPGG": 1.6, "RPGG_2012": 1.3, "RRZ_2008": 1.4, "Satzung_OEGK_2025": 1.4, "KrankenO_OEGK_2025": 1.2,
    "RRK_2021": 1.3, "RUF_2020": 1.2, "KBGG": 1.3, "FLAG": 1.2, "MuKiPassV_2002": 1.2, "RVU": 1.2, "ASVG": 1.1,
}
_lock = threading.Lock()
_ready: Path | None = None


def _fingerprint() -> str:
    st = kpath(CORPUS).stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def _index_path() -> Path:
    return get_settings().var_dir / INDEX_NAME


def _build(path: Path, fp: str) -> None:
    tmp = path.with_suffix(f".tmp{os.getpid()}")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        con.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
        con.execute("CREATE VIRTUAL TABLE para USING fts5(heading, text, law_key UNINDEXED, rid UNINDEXED, "
                    "tokenize='unicode61 remove_diacritics 2')")
        con.executemany("INSERT INTO para(heading, text, law_key, rid) VALUES (?,?,?,?)",
                        [(r["heading"], r["text"], r["law_key"], i) for i, r in enumerate(rows())])
        con.execute("INSERT INTO meta VALUES ('fingerprint', ?)", (fp,))
        con.commit()
    finally:
        con.close()
    os.replace(tmp, path)


def ensure_index() -> Path:
    global _ready
    with _lock:
        fp = _fingerprint()
        path = _index_path()
        if _ready == path and path.exists():
            return path
        current = None
        if path.exists():
            try:
                with sqlite3.connect(path) as con:
                    current = con.execute("SELECT v FROM meta WHERE k='fingerprint'").fetchone()
            except sqlite3.DatabaseError:
                current = None
        if not current or current[0] != fp:
            _build(path, fp)
        _ready = path
        return path


def match_query(q: str) -> str | None:
    """User text -> FTS5 MATCH expression: each term quoted (no operator injection), prefix match, OR-combined."""
    terms = [t for t in re.findall(r"\w+", q.lower()) if len(t) > 2]
    if not terms:
        return None
    return " OR ".join(f'"{t}"*' for t in dict.fromkeys(terms))


def search(q: str, law: str | None = None, limit: int = 10) -> list[tuple[dict, float, str]]:
    """Returns (row, score, snippet), best first. Score = -bm25 × law boost (higher is better)."""
    expr = match_query(q)
    if expr is None:
        return []
    corpus = rows()
    sql = ("SELECT rid, law_key, -bm25(para, 3.0, 1.0) AS s, snippet(para, 1, '', '', ' … ', 40) FROM para "
           "WHERE para MATCH ?")
    args: list = [expr]
    if law:
        sql += " AND law_key = ? COLLATE NOCASE"
        args.append(law)
    sql += " ORDER BY bm25(para, 3.0, 1.0) LIMIT ?"
    args.append(max(limit * 5, 50))   # over-fetch, then re-rank with the law boost
    with sqlite3.connect(ensure_index()) as con:
        hits = con.execute(sql, args).fetchall()
    ranked = sorted(((corpus[rid], s * LAW_BOOST.get(lk, 1.0), snip) for rid, lk, s, snip in hits),
                    key=lambda h: -h[1])
    return [(r, round(s, 4), snip) for r, s, snip in ranked[:limit]]

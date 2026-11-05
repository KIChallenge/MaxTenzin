"""Read-only access to committed knowledge (knowledge/extracted + curated YAML). Cached in memory."""

from __future__ import annotations

import json
from functools import lru_cache

import yaml

from app.core.config import get_settings


def kpath(*parts: str):
    return get_settings().knowledge_dir.joinpath(*parts)


@lru_cache
def jsonl(rel: str) -> list[dict]:
    return [json.loads(x) for x in kpath(rel).read_text(encoding="utf-8").splitlines() if x.strip()]


@lru_cache
def json_file(rel: str):
    return json.loads(kpath(rel).read_text(encoding="utf-8"))


@lru_cache
def yaml_file(rel: str):
    p = kpath(rel)
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else None


def value(key: str, year: int = 2026) -> dict | None:
    for v in json_file("extracted/values/veraendw.json")["values"]:
        if v["key"] == key and v["year"] == year:
            return v
    return None

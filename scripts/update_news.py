#!/usr/bin/env python3
"""Collect official + UGT labour news. Stdlib only.

Merge rules:
- Identity is the canonical URL (not a hand-written slug).
- Editorial overlay in data/editorial.json is never overwritten by RSS.
- Pinned items survive the 14-day window.
- Unparseable dates are dropped, never treated as "now".
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
# Workspace layout: scripts/news/update_news.py → repo root /workspace
# GitHub Pages layout uses the same relative depth if placed at scripts/update_news.py.
# Detect both.
if (ROOT / "src" / "data" / "sources.json").exists():
    DATA = ROOT / "src" / "data"
    SOURCES_PATH = DATA / "sources.json"
    EDITORIAL_PATH = DATA / "editorial.json"
    OUT = DATA / "noticias.json"
else:
    ROOT = Path(__file__).resolve().parents[1]
    DATA = ROOT / "data"
    SOURCES_PATH = ROOT / "sources.json"
    EDITORIAL_PATH = DATA / "editorial.json"
    OUT = DATA / "noticias.json"

MAX_ITEMS = 250
LOOKBACK_DAYS = 14
UA = "NoticiasLaboralesPWA/1.1 (+https://github.com/ttttooonni/noticias-laborales)"
TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$)", re.I)
BOE_ID = re.compile(r"BOE-A-\d{4}-\d+", re.I)

KEYWORDS = {
    "laboral": [
        "laboral", "trabajo", "trabajador", "trabajadora", "jornada", "salario",
        "salarial", "convenio colectivo", "convenios colectivos", "despido", "vacaciones", "permiso", "igualdad laboral", "igualdad de género", "plan de igualdad",
        "conciliación", "cotización", "pensión", "seguridad social", "riesgo laboral",
        "prevención", "huelga", "negociación colectiva", "hostelería", "camarera",
        "camarero", "fijo discontinuo", "siniestralidad", "accidente de trabajo",
        "empleabilidad", "desempleo", "desemplead", "servicio canario de empleo",
    ],
    "sentencia": [
        "sentencia", "tribunal supremo", "tribunal superior de justicia",
        "audiencia nacional", "juzgado", "poder judicial", "sala de lo social", "ecli",
    ],
    "canarias": [
        "canarias", "las palmas", "tenerife", "gran canaria", "lanzarote",
        "fuerteventura", "la palma", "la gomera", "el hierro", "santa cruz de tenerife",
    ],
    "lasPalmas": [
        "las palmas", "gran canaria", "lanzarote", "fuerteventura", "provincia de las palmas",
    ],
    "hosteleria": [
        "hostelería", "hosteleria", "hotel", "hoteles", "restauración", "restauracion",
        "alojamiento", "camareras de piso", "camarero", "camarera", "hoteles escuela",
        "hecansa", "extra hotelero", "cocina", "recepción hotelera",
    ],
}
TOPIC_MAP = [
    ("Salarios", ["salario", "salarial", "sueldo", "retribución", "tablas salariales", "poder adquisitivo", "subida salarial"]),
    ("Jornada", ["jornada", "horas semanales", "tiempo de trabajo", "descanso", "turnos", "cuadrante"]),
    ("Convenios", ["convenio colectivo", "convenios colectivos", "negociación colectiva", "acuerdo parcial", "preacuerdo"]),
    ("Empleo", ["desempleo", "desemplead", "contratación", "empleabilidad", "servicio canario de empleo", "formación para personas", "abuso de temporalidad", "fijo discontinuo"]),
    ("Derechos laborales", ["despido", "permiso", "igualdad laboral", "igualdad de género", "plan de igualdad", "conciliación", "prevención", "accidente de trabajo", "siniestralidad", "derecho laboral", "riesgo laboral"]),
]


def fetch(url: str, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/html;q=0.8, */*;q=0.5"})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def decode_xml(raw: bytes) -> str:
    head = raw[:240]
    m = re.search(br'encoding=["\']([\w-]+)["\']', head, re.I)
    enc = (m.group(1).decode("ascii", "ignore") if m else "utf-8").lower()
    if enc in {"iso-8859-1", "latin1", "latin-1"}:
        enc = "cp1252"
    return raw.decode(enc, errors="replace")


def clean(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def canonicalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
    except Exception:
        return raw.rstrip("/")
    host = parts.hostname.replace("www.", "") if parts.hostname else ""
    host = host.lower()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not TRACKING.match(k)]
    boe = BOE_ID.search(raw)
    if boe and host.endswith("boe.es"):
        return f"https://www.boe.es/diario_boe/txt.php?id={boe.group(0).upper()}"
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit(("https", host, path or "/", urlencode(query), ""))


def make_id(url: str) -> str:
    boe = BOE_ID.search(url or "")
    if boe:
        return boe.group(0).lower()
    return hashlib.sha1(canonicalize_url(url).encode()).hexdigest()[:16]


def parse_date(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s[: len(fmt) + 8].replace("Z", "+0000") if "T" in s else s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def has_any(text: str, words: list[str]) -> bool:
    for w in words:
        if " " in w:
            if w in text:
                return True
        elif re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text, re.I):
            return True
    return False


def classify(text: str, source: dict) -> list[str]:
    cats = list(source.get("categories") or [])
    def add(c: str) -> None:
        if c not in cats:
            cats.append(c)
    if has_any(text, KEYWORDS["sentencia"]) or source.get("type") == "JUSTICIA":
        add("Sentencias")
    if has_any(text, KEYWORDS["canarias"]):
        add("Canarias")
    if has_any(text, KEYWORDS["lasPalmas"]):
        add("Las Palmas")
    if has_any(text, KEYWORDS["hosteleria"]):
        add("Hostelería")
    if source.get("type") == "UGT":
        add("UGT")
    for cat, words in TOPIC_MAP:
        if has_any(text, words):
            add(cat)
    return cats[:8]


def relevant(item: dict, source: dict | None) -> bool:
    stype = (source or {}).get("type") or item.get("source_type")
    sid = (source or {}).get("id") or ""
    if stype == "UGT":
        return True
    if sid.startswith("boe-"):
        return True
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    if stype == "JUSTICIA":
        return has_any(text, KEYWORDS["laboral"]) or has_any(text, KEYWORDS["sentencia"])
    return (
        has_any(text, KEYWORDS["laboral"])
        or has_any(text, KEYWORDS["hosteleria"])
        or has_any(text, KEYWORDS["sentencia"])
        or "Convenios" in (item.get("categories") or [])
    )


def local_tag(node: ET.Element) -> str:
    return (node.tag or "").split("}", 1)[-1].lower()


def child_text(node: ET.Element, *names: str) -> str:
    want = {n.lower() for n in names}
    for child in list(node):
        if local_tag(child) in want:
            return clean("".join(child.itertext()))
    return ""


def child_link(node: ET.Element) -> str:
    text = child_text(node, "link")
    if text.startswith("http"):
        return text
    for child in list(node):
        if local_tag(child) == "link":
            href = (child.attrib.get("href") or "").strip()
            rel = (child.attrib.get("rel") or "alternate").lower()
            if href.startswith("http") and rel in {"", "alternate", "self"}:
                return href
    guid = child_text(node, "guid", "id")
    return guid if guid.startswith("http") else ""


def parse_feed(raw: bytes, source: dict) -> list[dict]:
    xml = decode_xml(raw)
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    items = [n for n in root.iter() if local_tag(n) in {"item", "entry"}]
    out: list[dict] = []
    for node in items:
        title = child_text(node, "title")
        link = child_link(node)
        desc = child_text(node, "description", "summary", "content")
        pub = child_text(node, "pubdate", "published", "updated", "date")
        if not title or not link:
            continue
        d = parse_date(pub)
        if d is None:
            continue
        url = canonicalize_url(link)
        if not url.startswith("http"):
            continue
        text = (title + " " + desc).lower()
        kind = "sentencia" if source.get("type") == "JUSTICIA" or has_any(text, KEYWORDS["sentencia"]) else "noticia"
        out.append({
            "id": make_id(url),
            "title": title,
            "source": source["name"],
            "source_type": source["type"],
            "source_label": source["label"],
            "published": d.astimezone(timezone.utc).isoformat(),
            "categories": classify(text, source),
            "type": kind,
            "summary": desc[:360],
            "what_happened": desc[:700],
            "who_affected": "",
            "impact": "",
            "ugt_position": "",
            "url": url,
            "_weight": source.get("weight", 50),
        })
    return out


RSS_LINK_RE = re.compile(r'<link\b[^>]*type=["\']application/(?:rss|atom)\+xml["\'][^>]*>', re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
FEED_HINT = re.compile(r'(\?|&)format=feed|/feed/?(\?|$)|/rss/?(\?|$)|type=rss|type=atom', re.I)


def discover_feeds(html_text: str, page_url: str) -> list[str]:
    found: list[str] = []
    for m in RSS_LINK_RE.finditer(html_text):
        href = (HREF_RE.search(m.group(0)) or [None, ""])[1]
        if href:
            found.append(urljoin(page_url, href))
    for m in HREF_RE.finditer(html_text):
        href = m.group(1)
        if FEED_HINT.search(href):
            found.append(urljoin(page_url, href))
    seen: set[str] = set()
    out: list[str] = []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def collect_html(source: dict) -> list[dict]:
    raw = fetch(source["url"])
    html_text = raw.decode("utf-8", "replace")
    for feed in discover_feeds(html_text, source["url"])[:3]:
        try:
            items = parse_feed(fetch(feed), source)
            if items:
                return items
        except Exception:
            continue
    return []


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def index_editorial(raw: dict) -> dict[str, dict]:
    if not isinstance(raw, dict):
        return {}
    items = raw.get("items", raw)
    out = {}
    for url, fields in (items or {}).items():
        if isinstance(fields, dict):
            out[canonicalize_url(url)] = fields
    return out


PRESERVE = ("what_happened", "who_affected", "impact", "ugt_position", "summary", "title")


def apply_editorial(item: dict, editorial: dict[str, dict]) -> dict:
    url = canonicalize_url(item.get("url", ""))
    ed = editorial.get(url, {})
    item = dict(item)
    item["url"] = url
    item["id"] = make_id(url)
    for key in PRESERVE:
        val = ed.get(key)
        if isinstance(val, str) and val.strip():
            item[key] = val
    if ed.get("pin"):
        item["pin"] = True
    return item


def is_pinned(item: dict, editorial: dict[str, dict]) -> bool:
    if item.get("pin"):
        return True
    ed = editorial.get(canonicalize_url(item.get("url", "")), {})
    if ed.get("pin"):
        return True
    until = parse_date(str(ed.get("keep_until") or ""))
    return bool(until and until > datetime.now(timezone.utc))


def merge_item(store: dict[str, dict], incoming: dict, editorial: dict[str, dict]) -> None:
    fresh = apply_editorial(incoming, editorial)
    url = fresh["url"]
    if not url:
        return
    prev = store.get(url)
    if not prev:
        store[url] = fresh
        return
    merged = dict(fresh)
    for key in ("what_happened", "who_affected", "impact", "ugt_position"):
        merged[key] = (prev.get(key) or "").strip() or fresh.get(key) or ""
    merged["title"] = fresh.get("title") or prev.get("title")
    merged["summary"] = fresh.get("summary") or prev.get("summary")
    merged["pin"] = bool(prev.get("pin") or fresh.get("pin"))
    cats = []
    for c in (prev.get("categories") or []) + (fresh.get("categories") or []):
        if c not in cats:
            cats.append(c)
    merged["categories"] = cats[:8]
    ed = editorial.get(url, {})
    if ed.get("title"):
        merged["title"] = ed["title"]
    if ed.get("summary"):
        merged["summary"] = ed["summary"]
    if ed.get("what_happened"):
        merged["what_happened"] = ed["what_happened"]
    store[url] = merged


def main() -> None:
    config = load_json(SOURCES_PATH, {"sources": []})
    editorial = index_editorial(load_json(EDITORIAL_PATH, {}))
    seed = load_json(DATA / "seed.json", {"items": []})
    old = load_json(OUT, {"items": []})
    store: dict[str, dict] = {}
    for item in (seed.get("items") or []) + (old.get("items") or []):
        merge_item(store, item, editorial)
    failures = []
    sources = [s for s in config.get("sources", []) if s.get("enabled", True) is not False]
    for source in sources:
        try:
            if source.get("kind") == "html":
                collected = collect_html(source)
            elif source.get("kind") == "rss":
                collected = parse_feed(fetch(source["url"]), source)
            else:
                continue
            for item in collected:
                merge_item(store, item, editorial)
        except Exception as e:
            failures.append({"source": source.get("name", "?"), "error": str(e)})
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    by_source = {s["name"]: s for s in config.get("sources", [])}

    def keep(item: dict) -> bool:
        if is_pinned(item, editorial):
            return True
        d = parse_date(item.get("published", ""))
        if d is None or d < cutoff:
            return False
        return relevant(item, by_source.get(item.get("source", "")))

    kept = [it for it in store.values() if keep(it)]

    def sort_key(it: dict):
        d = parse_date(it.get("published", "")) or datetime.min.replace(tzinfo=timezone.utc)
        return (d, it.get("_weight", 0))

    items = sorted(kept, key=sort_key, reverse=True)[:MAX_ITEMS]
    for it in items:
        it.pop("_weight", None)
    DATA.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")
    payload = {
        "updated_at": now,
        "items": items,
        "health": {"sources_checked": len(sources), "failures": failures},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(items)} noticias conservadas; {len(failures)} fuentes con error.")
    for f in failures:
        print("WARN", f)


if __name__ == "__main__":
    main()

"""Busca y descarga el PDF del menú en la web del cole.

La web es un Google Sites que incrusta el PDF desde Google Drive, así que
buscamos identificadores de archivos de Drive en el HTML (y, por si acaso,
enlaces directos a .pdf) y elegimos el que mejor encaje (palabra BASAL y mes).
"""
import html
import re
import unicodedata
from dataclasses import dataclass

import requests

from . import config

UA = {"User-Agent": "Mozilla/5.0 (menu-familiar; +https://github.com/jesusgarrigues/menu-familiar)"}

MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]

DRIVE_PATTERNS = [
    r"drive\.google\.com/file/d/([-\w]{20,})",
    r"docs\.google\.com/file/d/([-\w]{20,})",
    r"drive\.google\.com/(?:uc|open)\?(?:[^\"'\s<>]*?&(?:amp;)?)?id=([-\w]{20,})",
    r"drive\.usercontent\.google\.com/download\?(?:[^\"'\s<>]*?&(?:amp;)?)?id=([-\w]{20,})",
    r"data-embed-doc-id=\"([-\w]{20,})\"",
    r"\"([-\w]{28,44})\",\s*\"[^\"]*\.pdf\"",   # datos JSON incrustados de Sites
]


@dataclass
class Candidate:
    url: str
    kind: str          # 'drive' | 'pdf'
    ident: str
    context: str       # texto alrededor (para saber el nombre del archivo)
    title: str = ""    # nombre de archivo .pdf más cercano
    score: float = 0.0


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()


def find_candidates(page_html: str, base_url: str = "") -> list[Candidate]:
    raw = html.unescape(page_html)
    found: dict[str, Candidate] = {}
    for pat in DRIVE_PATTERNS:
        for m in re.finditer(pat, raw):
            fid = m.group(1)
            if fid in found:
                continue
            ctx = raw[max(0, m.start() - 1500): m.end() + 1500]
            found[fid] = Candidate(
                url=f"https://drive.google.com/uc?export=download&id={fid}",
                kind="drive", ident=fid, context=ctx, title=_nearest_title(raw, m.start(), m.end()),
            )
    for m in re.finditer(r"href=\"([^\"]+\.pdf(?:\?[^\"]*)?)\"", raw, re.I):
        url = requests.compat.urljoin(base_url, m.group(1))
        if url not in found:
            found[url] = Candidate(url=url, kind="pdf", ident=url,
                                   context=raw[max(0, m.start() - 800): m.end() + 800],
                                   title=_nearest_title(raw, m.start(), m.end()) or url.rsplit("/", 1)[-1])
    return list(found.values())


TITLE_RE = re.compile(r"([^<>\"\n/]{3,90}?\.pdf)\b", re.I)


def _nearest_title(raw: str, start: int, end: int, reach: int = 3000) -> str:
    best, best_d = "", reach + 1
    lo = max(0, start - reach)
    for m in TITLE_RE.finditer(raw, lo, min(len(raw), end + reach)):
        d = (start - m.end()) if m.end() <= start else max(0, m.start() - end)
        if d < best_d:
            best, best_d = m.group(1).strip(" >"), d
    return best


def score(c: Candidate, year: int, month: int) -> float:
    ctx = norm(c.title or c.context)
    s = 0.0
    if ".pdf" in ctx:
        s += 1
    kw = norm(config.SCHOOL_MENU_KEYWORD)
    if kw and kw in ctx:
        s += 3
    if MONTHS[month - 1] in ctx:
        s += 4
    if str(year) in ctx:
        s += 1
    for bad in ("alerg", "sin gluten", "celiac", "vegetar", "precio", "normas"):
        if bad in ctx:
            s -= 1.5
    if "menu" in ctx or "comedor" in ctx:
        s += 0.5
    return s


def guess_title(c: Candidate) -> str:
    return c.title


def fetch_page(url: str | None = None) -> str:
    r = requests.get(url or config.SCHOOL_MENU_URL, headers=UA, timeout=30)
    r.raise_for_status()
    return r.text


def download_pdf(c: Candidate) -> bytes:
    urls = [c.url]
    if c.kind == "drive":
        urls += [
            f"https://drive.usercontent.google.com/download?id={c.ident}&export=download&confirm=t",
            f"https://drive.google.com/uc?export=download&confirm=t&id={c.ident}",
        ]
    last = None
    s = requests.Session()
    for u in urls:
        try:
            r = s.get(u, headers=UA, timeout=60, allow_redirects=True)
            if r.ok and r.content[:5] == b"%PDF-":
                return r.content
            # página de aviso de "no se puede analizar en busca de virus"
            m = re.search(r'name="uuid" value="([^"]+)"', r.text or "")
            if m and c.kind == "drive":
                r2 = s.get("https://drive.usercontent.google.com/download",
                           params={"id": c.ident, "export": "download", "confirm": "t", "uuid": m.group(1)},
                           headers=UA, timeout=60)
                if r2.ok and r2.content[:5] == b"%PDF-":
                    return r2.content
            last = f"{u} -> HTTP {r.status_code}, no es un PDF"
        except requests.RequestException as e:
            last = f"{u} -> {e}"
    raise RuntimeError(f"No se pudo descargar el PDF ({last})")


def find_best(year: int, month: int, page_html: str | None = None) -> Candidate | None:
    page_html = page_html if page_html is not None else fetch_page()
    cands = find_candidates(page_html, config.SCHOOL_MENU_URL)
    if not cands:
        return None
    for c in cands:
        c.score = score(c, year, month)
    cands.sort(key=lambda c: c.score, reverse=True)
    return cands[0]

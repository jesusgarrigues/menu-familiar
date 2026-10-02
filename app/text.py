"""Limpieza de textos del menú: mayúsculas, códigos de alérgenos y nombres de archivo."""
import re
import unicodedata

ALLERGEN_RE = re.compile(r"\(\s*(\d{1,2}(?:\s*[,.;y\-/]\s*\d{1,2})*)\s*\)")
LOWER_WORDS = {"de", "del", "con", "y", "e", "a", "al", "la", "las", "el", "los", "en", "su", "o", "u", "sin", "para", "por"}
KEEP_UPPER = {"BBQ"}

# Tabla oficial de los 14 alérgenos (Reglamento UE 1169/2011), numeración habitual en comedores
ALLERGENS = {
    1: "Gluten", 2: "Crustáceos", 3: "Huevo", 4: "Pescado", 5: "Cacahuete", 6: "Soja", 7: "Leche",
    8: "Frutos de cáscara", 9: "Apio", 10: "Mostaza", 11: "Sésamo", 12: "Sulfitos", 13: "Altramuces", 14: "Moluscos",
}


def _mostly_upper(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.7


def sentence_case(s: str) -> str:
    if not _mostly_upper(s):
        return s
    words = s.lower().split(" ")
    out = []
    for i, w in enumerate(words):
        if w.upper() in KEEP_UPPER:
            out.append(w.upper())
        elif i == 0:
            out.append(w[:1].upper() + w[1:])
        else:
            out.append(w)
    return " ".join(out)


def clean_dish(text: str) -> tuple[str, list[int]]:
    """'PAELLA MIXTA (2,14)' -> ('Paella mixta', [2, 14])."""
    text = (text or "").strip()
    allergens: list[int] = []
    for m in ALLERGEN_RE.finditer(text):
        for n in re.findall(r"\d{1,2}", m.group(1)):
            v = int(n)
            if 1 <= v <= 14 and v not in allergens:
                allergens.append(v)
    name = ALLERGEN_RE.sub("", text)
    name = re.sub(r"\s+", " ", name).strip(" ,.;-·")
    name = re.sub(r"\s+([,.;])", r"\1", name)
    return sentence_case(name), sorted(allergens)


def clean_title(title: str) -> str:
    t = (title or "").strip()
    t = re.sub(r"^(drive|google drive)\s*[,:\-]\s*", "", t, flags=re.I)
    t = re.sub(r"\.pdf$", "", t, flags=re.I).strip()
    return t


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower()

"""Algorytmy tekstowe: normalizacja nazw, rozbijanie adresów i podobieństwo opisów.

Czyste funkcje (bez Django i bez bazy), deterministyczne i jawne: wynik da się wytłumaczyć i powtórzyć.
"""

import difflib
import re
import unicodedata
from typing import Any, NamedTuple, Optional


def norm(text: Any) -> str:
    """Tekst w postaci porównywalnej: małe litery, bez polskich znaków i interpunkcji."""
    s = str(text).lower().replace("ł", "l")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:  # NaN
        return None
    text = re.sub(r"\s+", " ", str(value)).strip(" ,;")
    return text or None


# --------------------------------------------------------------------------- #
# Adresy
# --------------------------------------------------------------------------- #

POSTAL_RE = re.compile(r"\b(\d{2})-(\d{3})\b")
_STREET_PREFIXES = (
    (re.compile(r"^(ulica|ul)\b\.?\s*", re.I), "ul. "),
    (re.compile(r"^(aleja|aleje|al)\b\.?\s*", re.I), "al. "),
    (re.compile(r"^(plac|pl)\b\.?\s*", re.I), "pl. "),
    (re.compile(r"^(osiedle|os)\b\.?\s*", re.I), "os. "),
)


class Address(NamedTuple):
    street: Optional[str]
    city: Optional[str]
    postal: Optional[str]


def _normalize_street_prefix(street: str) -> str:
    for pattern, replacement in _STREET_PREFIXES:
        if pattern.match(street):
            return pattern.sub(replacement, street, count=1).strip()
    return street


def _strip_trailing_city(street: str, city: Optional[str]) -> str:
    """„ul. Bydgoska 17/21 Łódź” przy znanym mieście „Łódź”: miasto nie należy do ulicy."""
    if city and norm(street).endswith(" " + norm(city)):
        return street[: len(street) - len(city)].strip(" ,;")
    return street


def _split_postal(text: str, city: Optional[str]):
    """Wyjmuje kod pocztowy; tekst po kodzie to miejscowość (gdy jej nie znamy). Zwraca (tekst, miasto, kod)."""
    match = POSTAL_RE.search(text)
    if not match:
        return text, city, None
    postal = f"{match.group(1)}-{match.group(2)}"
    after = text[match.end() :].strip(" ,;")
    if after and not city:
        city = after.split(",")[0].strip()
    return text[: match.start()].strip(" ,;"), city, postal


def normalize_address(street: Any, city: Any = None) -> Address:
    """Rozbija i ujednolica adres.

    „ulica Paradna 36, 93-345 Łódź” -> ulica „ul. Paradna 36”, miasto „Łódź”, kod „93-345”.
    Miejscowość podana osobno ma pierwszeństwo. Kod pocztowy bez myślnika nie jest rozpoznawany
    (łatwo go pomylić z numerem budynku).
    """
    text, city_value = _clean(street), _clean(city)
    postal = None
    if text:
        text, city_value, postal = _split_postal(text, city_value)
        parts = [p.strip() for p in text.split(",") if p.strip()]
        if len(parts) > 1 and not city_value and not any(ch.isdigit() for ch in parts[-1]):
            city_value = parts.pop()
        text = _strip_trailing_city(", ".join(parts), city_value) if parts else None
        if text:
            text = _normalize_street_prefix(text) or None
    return Address(text, city_value, postal)


# --------------------------------------------------------------------------- #
# Podobieństwo opisów miejsc
# --------------------------------------------------------------------------- #

_STOP_TOKENS = {"ul", "al", "pl", "os", "ulica", "aleja", "plac", "osiedle", "w", "na", "przy", "i"}
_NUMBER_RE = re.compile(r"\d+[a-z]?")
DIFFERENT_NUMBER_CAP = 0.3


def _tokens(text: Any) -> list:
    cleaned = _clean(text)
    return [t for t in norm(cleaned).split() if t not in _STOP_TOKENS] if cleaned else []


def text_similarity(a: Any, b: Any) -> Optional[float]:
    """Podobieństwo dwóch opisów miejsca (0..1) albo None, gdy któryś jest pusty.

    Maksimum z podobieństwa zbiorów słów i podobieństwa ciągów znaków. Różne numery budynków
    („Floriańska 1” i „Floriańska 10”) to różne miejsca, więc wynik jest ograniczony do 0,3.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return None
    sa, sb = set(ta), set(tb)
    jaccard = len(sa & sb) / len(sa | sb)
    ratio = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    score = max(jaccard, ratio)
    na, nb = set(_NUMBER_RE.findall(norm(a))), set(_NUMBER_RE.findall(norm(b)))
    if na and nb and na != nb:
        score = min(score, DIFFERENT_NUMBER_CAP)
    return round(score, 4)

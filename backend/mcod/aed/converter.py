"""Konwerter: dowolny plik z listą AED -> wzorcowy układ wykazu AED.

Bez AI w działaniu - wszystko to jawne reguły, więc wynik jest powtarzalny:

1. mapowanie kolumn: profil źródła -> słownik synonimów -> podobieństwo nazw ->
   rozpoznanie po zawartości (zakresy współrzędnych, daty, TERYT, układ PL-1992),
2. normalizacja wartości (współrzędne w różnych zapisach, słowniki dostępności,
   dostępu i statusu, daty),
3. walidacja tymi samymi regułami co przy scalaniu (``check_row``),
4. raport: co poprawiono, co odrzucono i dlaczego.

Dane, których źródło nie podaje (np. data weryfikacji), NIE są zgadywane: trzeba je
podać jawnie jako wartość domyślną, inaczej wiersz jest odrzucany.
"""

import datetime
import difflib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from mcod.aed.constants import (
    AED_COLUMNS,
    COL_ACCESS,
    COL_AVAILABILITY,
    COL_CITY,
    COL_CONTACT,
    COL_HOURS,
    COL_ID,
    COL_LAT,
    COL_LOCATION,
    COL_LON,
    COL_OBJECT_TYPE,
    COL_STATUS,
    COL_STREET,
    COL_TERYT,
    COL_VERIFIED,
    MAIN_AED_REQUIRED_SOURCE_COLUMNS,
    POLAND_LAT_RANGE,
    POLAND_LON_RANGE,
)
from mcod.aed.text import norm, normalize_address

PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
FUZZY_THRESHOLD = 0.82

# Kolumny wzorca (bez "Lp."), które konwerter potrafi wypełnić.
TARGET_COLUMNS: List[str] = [c for c in AED_COLUMNS if c != "Lp."]


# Synonimy nazw kolumn (w postaci znormalizowanej). Telefon celowo pominięty: to często dane osobowe.
SYNONYMS: Dict[str, List[str]] = {
    COL_ID: [
        "id",
        "identyfikator",
        "identyfikator aed",
        "id aed",
        "aed id",
        "id urzadzenia",
        "nr",
        "numer",
        "numer aed",
        "nr aed",
        "nr ewid",
        "nr ewidencyjny",
        "numer ewidencyjny",
        "kod aed",
    ],
    COL_LAT: ["lat", "latitude", "szerokosc", "szerokosc geograficzna", "szer", "szer geogr", "geo lat", "wsp b"],
    COL_LON: ["lon", "lng", "long", "longitude", "dlugosc", "dlugosc geograficzna", "dl", "dl geogr", "geo lon", "wsp l"],
    COL_CITY: ["miejscowosc", "gmina", "miasto", "city", "town", "locality", "addr city"],
    COL_STREET: ["ulica i numer", "ulica", "adres", "address", "ulica nr", "street", "ulica numer"],
    COL_TERYT: ["kod teryt gminy", "teryt", "kod teryt", "teryt gminy", "terc"],
    COL_LOCATION: ["opis lokalizacji", "lokalizacja", "opis miejsca", "miejsce", "location", "umiejscowienie", "gdzie", "opis"],
    COL_OBJECT_TYPE: ["rodzaj obiektu", "typ obiektu", "obiekt", "rodzaj", "kategoria", "object type"],
    COL_AVAILABILITY: ["dostepnosc", "availability", "czas dostepnosci"],
    COL_HOURS: [
        "godziny dostepnosci",
        "godziny",
        "godziny otwarcia",
        "opening hours",
        "godziny pracy",
        "godz dostepu",
        "godziny dostepu",
        "godz dostepnosci",
        "godz otwarcia",
        "godz",
        "czas pracy",
    ],
    COL_ACCESS: ["sposob dostepu", "dostep", "access", "rodzaj dostepu"],
    COL_STATUS: ["status urzadzenia", "status", "stan", "stan urzadzenia", "sprawnosc"],
    COL_VERIFIED: [
        "data ostatniej weryfikacji",
        "data weryfikacji",
        "ostatnia weryfikacja",
        "weryfikacja",
        "data kontroli",
        "data przegladu",
        "check date",
        "data aktualizacji",
        "aktualizacja",
    ],
    COL_CONTACT: ["kontakt instytucjonalny", "kontakt", "email", "e mail", "mail", "contact"],
}


# --------------------------------------------------------------------------- #
# Parsowanie wartości
# --------------------------------------------------------------------------- #

_DMS = re.compile(r"""(\d+)\s*[°º\s]\s*(\d+)\s*['′’\s]\s*(\d+(?:[.,]\d+)?)\s*["″”]?\s*([NSEWnsew])?""")
_WKT_POINT = re.compile(r"POINT\s*\(\s*(-?\d+(?:[.,]\d+)?)\s+(-?\d+(?:[.,]\d+)?)\s*\)", re.I)
_NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def _blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip() == ""


def in_lat(v: float) -> bool:
    return POLAND_LAT_RANGE[0] <= v <= POLAND_LAT_RANGE[1]


def in_lon(v: float) -> bool:
    return POLAND_LON_RANGE[0] <= v <= POLAND_LON_RANGE[1]


def parse_coordinate(value: Any) -> Optional[float]:
    """Liczba, liczba z przecinkiem dziesiętnym albo zapis stopniowy (50°03'41"N)."""
    if _blank(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    m = _DMS.search(text)
    if m:
        deg, minutes, seconds = int(m.group(1)), int(m.group(2)), float(m.group(3).replace(",", "."))
        result = deg + minutes / 60 + seconds / 3600
        if m.group(4) and m.group(4).upper() in ("S", "W"):
            result = -result
        return result
    try:
        return float(text.replace(",", ".").replace(" ", ""))
    except ValueError:
        return None


def parse_point(value: Any) -> Optional[Tuple[float, float]]:
    """Punkt zapisany w jednej komórce: WKT ``POINT(lon lat)`` albo dwie liczby. Zwraca (lat, lon)."""
    if _blank(value):
        return None
    text = str(value)
    m = _WKT_POINT.search(text)
    if m:
        lon, lat = (float(g.replace(",", ".")) for g in m.groups())
        return (lat, lon) if in_lat(lat) and in_lon(lon) else None
    nums = _NUM.findall(text)
    if len(nums) != 2:
        return None
    a, b = (float(n.replace(",", ".")) for n in nums)
    if in_lat(a) and in_lon(b):
        return a, b
    if in_lat(b) and in_lon(a):
        return b, a
    return None


_T2180 = None


def from_pl1992(easting: float, northing: float) -> Optional[Tuple[float, float]]:
    """Współrzędne w układzie PL-1992 (EPSG:2180) -> (lat, lon) WGS84.

    Kolejność osi trzeba znać z góry: zamienione osie też często dają punkt w Polsce, więc nie da się jej
    wiarygodnie odgadnąć po wyniku. Wynik jest tylko sprawdzany pod kątem położenia w Polsce.
    """
    global _T2180
    try:
        if _T2180 is None:
            from pyproj import Transformer

            _T2180 = Transformer.from_crs(2180, 4326, always_xy=True)
        lon, lat = _T2180.transform(easting, northing)
    except Exception:  # noqa: BLE001
        return None
    return (lat, lon) if in_lat(lat) and in_lon(lon) else None


def parse_date(value: Any) -> Optional[datetime.date]:
    if _blank(value):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        parsed = pd.to_datetime(text[:10], errors="coerce")
    else:
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    return None if pd.isna(parsed) else parsed.date()


def parse_teryt(value: Any) -> Optional[str]:
    if _blank(value):
        return None
    digits = re.sub(r"\D", "", str(value).split(".")[0])
    if not digits:
        return None
    return digits.zfill(7) if len(digits) <= 7 else digits


def normalize_availability(value: Any, hours: Any = None) -> Optional[str]:
    text = norm(value) if not _blank(value) else ""
    h = norm(hours) if not _blank(hours) else ""
    both = f"{text} {h}"
    if any(k in both for k in ("calodob", "24 7", "24h", "24 h", "cala dob", "non stop", "nonstop", "zawsze")):
        return "całodobowo"
    # literówki w pojedynczym słowie, np. "caołobowo": tylko dla wartości bez cyfr (nie dla godzin typu 8.00-18.00)
    for part in (text, h):
        if (
            part
            and not any(ch.isdigit() for ch in part)
            and difflib.get_close_matches(part.replace(" ", ""), ["calodobowo", "calodobowe", "calodobowy"], n=1, cutoff=0.8)
        ):
            return "całodobowo"
    if "ograniczon" in text:
        return "ograniczona"
    if "godzin" in text or h:
        return "w godzinach"
    return None  # za mało informacji (np. samo "tak"): wymaga jawnej wartości domyślnej


def normalize_access(value: Any) -> Optional[str]:
    if _blank(value):
        return None
    t = norm(value)
    if t in ("no", "nie", "private") or any(k in t for k in ("klucz", "zamkniet", "prywatn")):
        return "zamknięte na klucz"
    if t == "customers" or any(k in t for k in ("zgod", "klient", "na prosbe", "recepcj", "portier", "pracownik")):
        return "za zgodą"
    if t in ("yes", "tak", "permissive", "public") or any(k in t for k in ("swobodn", "publiczn", "otwart", "ogolnodostep")):
        return "swobodny"
    return None


def normalize_status(value: Any) -> Optional[str]:
    if _blank(value):
        return None
    t = norm(value)
    if any(k in t for k in ("nieczynn", "uszkodz", "zepsut", "niesprawn", "wylaczon", "disused")):
        return "nieczynny"
    if any(k in t for k in ("weryfikac", "nieznan", "sprawdz")):
        return "do weryfikacji"
    if t in ("czynny", "sprawny", "dziala", "aktywny", "ok", "working", "tak", "yes") or "czynn" in t or "sprawn" in t:
        return "czynny"
    return None


# --------------------------------------------------------------------------- #
# Mapowanie kolumn
# --------------------------------------------------------------------------- #


@dataclass
class ColumnMatch:
    sources: List[str]
    confidence: float
    method: str  # profil | nazwa | podobieństwo | zawartość


@dataclass
class Mapping:
    columns: Dict[str, ColumnMatch] = field(default_factory=dict)
    pl1992: Optional[Tuple[str, str]] = None  # (kolumna wschodnia, kolumna północna)
    combined_point: Optional[str] = None

    def missing_required(self, defaults: Dict[str, Any]) -> List[str]:
        out = []
        for col in MAIN_AED_REQUIRED_SOURCE_COLUMNS:
            if col in self.columns or col in defaults:
                continue
            if col == COL_AVAILABILITY and COL_HOURS in self.columns:
                continue  # dostępność wyprowadzana z godzin
            if col in (COL_LAT, COL_LON) and (self.pl1992 or self.combined_point):
                continue
            out.append(col)
        return out

    def as_dict(self) -> Dict[str, Any]:
        return {
            "columns": {
                k: {"zrodlo": v.sources, "pewnosc": round(v.confidence, 2), "metoda": v.method} for k, v in self.columns.items()
            },
            "pl1992": list(self.pl1992) if self.pl1992 else None,
            "pojedyncza_kolumna_punktu": self.combined_point,
        }


def _numeric_fraction(series: pd.Series, test) -> float:
    vals = [v for v in series if not _blank(v)]
    if not vals:
        return 0.0
    ok = 0
    for v in vals:
        n = parse_coordinate(v)
        if n is not None and test(n):
            ok += 1
    return ok / len(vals)


def _date_fraction(series: pd.Series) -> float:
    vals = [v for v in series if not _blank(v)]
    if not vals:
        return 0.0
    return sum(1 for v in vals if parse_date(v) is not None and not isinstance(v, (int, float))) / len(vals)


def load_profile(name_or_path: str) -> Dict[str, Any]:
    path = Path(name_or_path)
    if not path.exists():
        path = PROFILES_DIR / f"{name_or_path}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _names_for(target: str) -> set:
    return {norm(target), *SYNONYMS.get(target, [])}


def _assign(mapping: Mapping, used: set, target: str, sources: List[str], confidence: float, method: str) -> None:
    mapping.columns[target] = ColumnMatch(list(sources), confidence, method)
    used.update(sources)


def _first_free_column(columns: List[Any], used: set, predicate) -> Optional[Any]:
    return next((c for c in columns if c not in used and predicate(c)), None)


def _map_by_profile(mapping: Mapping, used: set, columns: List[Any], profile: Optional[Dict[str, Any]]) -> None:
    """Profil źródła: jawna konfiguracja, wartość może być listą kandydatów."""
    for target, spec in ((profile or {}).get("columns") or {}).items():
        candidates = [spec] if isinstance(spec, str) else list(spec)
        found = [c for c in candidates if c in columns]
        if found:
            _assign(mapping, used, target, found, 1.0, "profil")


def _map_by_name(mapping: Mapping, used: set, columns: List[Any]) -> None:
    """Dokładna nazwa lub synonim."""
    for target in TARGET_COLUMNS:
        if target in mapping.columns:
            continue
        names = _names_for(target)
        col = _first_free_column(columns, used, lambda c: norm(c) in names)
        if col is not None:
            _assign(mapping, used, target, [col], 1.0, "nazwa")


def _map_by_prefix(mapping: Mapping, used: set, columns: List[Any]) -> None:
    """Nazwa zaczyna się od synonimu (np. "lokalizacja w budynku" -> opis lokalizacji)."""
    for target in TARGET_COLUMNS:
        if target in mapping.columns:
            continue
        synonyms = SYNONYMS.get(target, [])
        col = _first_free_column(columns, used, lambda c: any(len(n) >= 5 and norm(c).startswith(n + " ") for n in synonyms))
        if col is not None:
            _assign(mapping, used, target, [col], 0.85, "prefiks nazwy")


def _map_by_similarity(mapping: Mapping, used: set, columns: List[Any]) -> None:
    """Podobieństwo nazw: wszystkie pary naraz, przydział od najlepszego wyniku.

    Inaczej "Godz. dostępu" trafiałoby do "Sposobu dostępu" tylko dlatego, że ta kolumna wzorca jest wcześniej.
    """
    pairs = []
    for target in TARGET_COLUMNS:
        if target in mapping.columns:
            continue
        names = _names_for(target)
        for col in columns:
            if col in used:
                continue
            ratio = max(difflib.SequenceMatcher(None, norm(col), name).ratio() for name in names)
            if ratio >= FUZZY_THRESHOLD:
                pairs.append((ratio, target, col))
    for ratio, target, col in sorted(pairs, key=lambda x: -x[0]):
        if target not in mapping.columns and col not in used:
            _assign(mapping, used, target, [col], ratio, "podobieństwo")


_CONTENT_RULES = (
    (COL_LAT, lambda series: _numeric_fraction(series, in_lat) >= 0.8),
    (COL_LON, lambda series: _numeric_fraction(series, in_lon) >= 0.8),
    (COL_VERIFIED, lambda series: _date_fraction(series) >= 0.8),
)


def _map_by_content(mapping: Mapping, used: set, columns: List[Any], df: pd.DataFrame) -> None:
    """Po zawartości kolumny: zakres współrzędnych, daty."""
    for col in columns:
        if col in used:
            continue
        for target, test in _CONTENT_RULES:
            if target not in mapping.columns and test(df[col]):
                _assign(mapping, used, target, [col], 0.7, "zawartość")
                break


def _is_point_column(series: pd.Series) -> bool:
    vals = [v for v in series if not _blank(v)]
    return bool(vals) and sum(1 for v in vals if parse_point(v)) / len(vals) >= 0.8


def _map_other_coordinates(mapping: Mapping, used: set, columns: List[Any], df: pd.DataFrame) -> None:
    """Współrzędne w innym zapisie: pojedyncza kolumna albo układ PL-1992."""
    if COL_LAT in mapping.columns and COL_LON in mapping.columns:
        return
    point_col = _first_free_column(columns, used, lambda c: _is_point_column(df[c]))
    if point_col is not None:
        mapping.combined_point = point_col
        used.add(point_col)
        return
    big = [c for c in columns if c not in used and _numeric_fraction(df[c], lambda n: 1e5 <= n <= 1e6) >= 0.8]
    if len(big) >= 2:
        mapping.pl1992 = (big[0], big[1])
        used.update(big[:2])


def map_columns(df: pd.DataFrame, profile: Optional[Dict[str, Any]] = None) -> Mapping:
    mapping = Mapping()
    used: set = set()
    columns = list(df.columns)
    _map_by_profile(mapping, used, columns, profile)
    _map_by_name(mapping, used, columns)
    _map_by_prefix(mapping, used, columns)
    _map_by_similarity(mapping, used, columns)
    _map_by_content(mapping, used, columns, df)
    _map_other_coordinates(mapping, used, columns, df)
    return mapping


# --------------------------------------------------------------------------- #
# Konwersja
# --------------------------------------------------------------------------- #


def _first_value(row: pd.Series, match: Optional[ColumnMatch]) -> Any:
    if not match:
        return None
    for src in match.sources:
        value = row.get(src)
        if not _blank(value):
            return value.strip() if isinstance(value, str) else value
    return None


ADDRESS_ONLY_ERROR = (
    "brak współrzędnych (jest adres). Konwerter nie geokoduje adresów; na dane.gov.pl portal potrafi je "
    "wyliczyć własnym geokoderem, w środowisku lokalnym niedostępnym. Uzupełnij współrzędne u dysponenta"
)


def _coordinates_from_alternatives(raw: pd.Series, mapping: Mapping, lat, lon, notes: List[str]):
    """Gdy brak lat/lon w osobnych kolumnach: pojedyncza kolumna punktu albo układ PL-1992."""
    if mapping.combined_point:
        pt = parse_point(raw.get(mapping.combined_point))
        if pt:
            notes.append("współrzędne z jednej kolumny")
            return pt
    if mapping.pl1992:
        a, b = parse_coordinate(raw.get(mapping.pl1992[0])), parse_coordinate(raw.get(mapping.pl1992[1]))
        pt = from_pl1992(a, b) if a is not None and b is not None else None
        if pt:
            notes.append("przeliczono z PL-1992 (EPSG:2180); przyjęto: pierwsza kolumna = wschód, druga = północ")
            return pt
    return lat, lon


def _resolve_coordinates(raw: pd.Series, get, mapping: Mapping):
    notes: List[str] = []
    lat, lon = parse_coordinate(get(COL_LAT)), parse_coordinate(get(COL_LON))
    if lat is None or lon is None:
        lat, lon = _coordinates_from_alternatives(raw, mapping, lat, lon, notes)
    if lat is not None and lon is not None:
        if not (in_lat(lat) and in_lon(lon)) and in_lat(lon) and in_lon(lat):
            lat, lon = lon, lat
            notes.append("zamieniono szerokość z długością")
        lat, lon = round(lat, 6), round(lon, 6)
    return lat, lon, notes


def _row_values(get, lat, lon) -> Dict[str, Any]:
    hours = get(COL_HOURS)
    availability = normalize_availability(get(COL_AVAILABILITY), hours)
    if availability is None and not _blank(hours):
        availability = normalize_availability(None, hours)
    verified = parse_date(get(COL_VERIFIED))
    ident = get(COL_ID)
    city = get(COL_CITY)
    if _blank(city):
        city = normalize_address(get(COL_STREET)).city  # „ul. Paradna 36, 93-345 Łódź” -> Łódź
    return {
        COL_ID: str(ident).strip() if ident is not None else None,
        COL_LAT: lat,
        COL_LON: lon,
        COL_CITY: city,
        COL_STREET: get(COL_STREET),
        COL_TERYT: parse_teryt(get(COL_TERYT)),
        COL_LOCATION: get(COL_LOCATION),
        COL_OBJECT_TYPE: get(COL_OBJECT_TYPE),
        COL_AVAILABILITY: availability,
        COL_HOURS: hours,
        COL_ACCESS: normalize_access(get(COL_ACCESS)),
        COL_STATUS: normalize_status(get(COL_STATUS)),
        COL_VERIFIED: verified.isoformat() if verified else None,
        COL_CONTACT: get(COL_CONTACT),
    }


def _apply_defaults(values: Dict[str, Any], defaults: Dict[str, Any], notes: List[str], id_prefix: str, number: int) -> None:
    """Wartości domyślne (jawne) tylko tam, gdzie źródło nic nie podaje; brakujący identyfikator jest nadawany."""
    for col, default in defaults.items():
        if col in values and _blank(values[col]):
            values[col] = default
            notes.append(f"wartość domyślna: {col}")
    if _blank(values[COL_ID]):
        values[COL_ID] = f"{id_prefix}-{number:04d}"
        notes.append("nadano identyfikator")


def _row_error(values: Dict[str, Any]) -> Optional[str]:
    from mcod.aed.utils import check_row  # unikamy cyklu importów

    error = check_row(pd.Series(values))
    no_coordinates = values[COL_LAT] is None or values[COL_LON] is None
    has_address = not (_blank(values[COL_STREET]) and _blank(values[COL_CITY]))
    if error and no_coordinates and has_address:
        return ADDRESS_ONLY_ERROR  # lista z samymi adresami: nie zgadujemy współrzędnych, ale mówimy, co dalej
    return error


def convert_dataframe(
    df: pd.DataFrame,
    profile: Optional[Dict[str, Any]] = None,
    defaults: Optional[Dict[str, Any]] = None,
    id_prefix: str = "AED",
    pl1992_north_first: bool = False,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], Mapping]:
    """Zwraca (DataFrame w układzie wzorca, raport wierszy, mapowanie)."""
    defaults = {**((profile or {}).get("defaults") or {}), **(defaults or {})}
    mapping = map_columns(df, profile)
    if mapping.pl1992 and pl1992_north_first:
        mapping.pl1992 = (mapping.pl1992[1], mapping.pl1992[0])
    report: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []

    for position, (idx, raw) in enumerate(df.iterrows(), start=1):
        get = lambda col: _first_value(raw, mapping.columns.get(col))  # noqa: E731
        lat, lon, notes = _resolve_coordinates(raw, get, mapping)
        values = _row_values(get, lat, lon)
        _apply_defaults(values, defaults, notes, id_prefix, position)  # numer wg pozycji w pliku, także dla odrzuconych
        error = _row_error(values)
        entry = {"wiersz": int(idx) + 2, "id": values[COL_ID]}
        if error:
            report.append({**entry, "wynik": "odrzucono", "szczegoly": error})
            continue
        rows.append(values)
        report.append({**entry, "wynik": "poprawiono" if notes else "ok", "szczegoly": "; ".join(notes)})

    out = pd.DataFrame(rows, columns=TARGET_COLUMNS)
    out.insert(0, "Lp.", range(1, len(out) + 1))
    return out[AED_COLUMNS], report, mapping


# --------------------------------------------------------------------------- #
# Wczytywanie plików wejściowych
# --------------------------------------------------------------------------- #


def read_any(path: str) -> pd.DataFrame:
    """csv / xls / xlsx / json (Overpass lub GeoJSON) -> DataFrame."""
    p = Path(path)
    ext = p.suffix.lower().lstrip(".")
    if ext in ("xlsx", "xls"):
        return pd.read_excel(p, dtype=object)
    if ext in ("json", "geojson"):
        return json_to_frame(json.loads(p.read_text(encoding="utf-8")))
    raw = p.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1250")
    import csv
    import io

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        sep = dialect.delimiter
    except csv.Error:
        sep = ","
    return pd.read_csv(io.StringIO(text), sep=sep, dtype=object)


def json_to_frame(data: Dict[str, Any]) -> pd.DataFrame:
    """Overpass JSON (``elements``) lub GeoJSON (``features``) -> DataFrame z kolumnami z tagów."""
    records: List[Dict[str, Any]] = []
    for el in data.get("elements", []):
        center = el.get("center") or {}
        rec = {
            "osm_id": f"osm-{el.get('type', 'node')}-{el.get('id')}",
            "lat": el.get("lat", center.get("lat")),
            "lon": el.get("lon", center.get("lon")),
        }
        rec.update(el.get("tags") or {})
        records.append(rec)
    for i, feat in enumerate(data.get("features", []), 1):
        coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
        rec = {"lat": coords[1] if len(coords) > 1 else None, "lon": coords[0]}
        rec.update(feat.get("properties") or {})
        records.append(rec)
    df = pd.DataFrame(records)
    if "addr:street" in df.columns:
        number = df["addr:housenumber"] if "addr:housenumber" in df.columns else ""
        df["_street"] = (
            df["addr:street"].fillna("").astype(str) + " " + pd.Series(number, index=df.index).fillna("").astype(str)
        ).str.strip()
        df["_street"] = df["_street"].replace("", None)
    return df

"""Logika wykazu AED - odpowiednik mcod.resources.dga_utils dla defibrylatorów.

Część "czysta" (pandas) nie dotyka bazy danych, dzięki czemu jest testowalna
bez środowiska Django. Część "bazodanowa" (zasoby, zbiór danych) jest
na końcu pliku.
"""

import datetime
import json
import logging
import math
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from mcod.aed.changes import diff_main
from mcod.aed.constants import (
    AED_COLUMNS,
    COL_AVAILABILITY,
    COL_CITY,
    COL_DAYS_SINCE,
    COL_FRESHNESS,
    COL_HOURS,
    COL_HOURS_NORM,
    COL_ID,
    COL_LAT,
    COL_LOCATION,
    COL_LON,
    COL_MERGE_CONF,
    COL_NOTES,
    COL_OTHER_PROVIDERS,
    COL_POSTAL,
    COL_PROVIDER,
    COL_SCOPE,
    COL_SOURCE_DATE,
    COL_SOURCE_RESOURCE,
    COL_SOURCES_COUNT,
    COL_STATUS,
    COL_STREET,
    COL_TRUST,
    COL_VERIFIED,
    DEDUP_CERTAIN_METERS,
    DEDUP_MAX_METERS,
    DEDUP_TEXT_MIN,
    ENUM_COLUMNS,
    FRESH_DAYS,
    FRESHNESS_ACTUAL,
    FRESHNESS_BROKEN,
    FRESHNESS_STALE,
    FRESHNESS_TO_VERIFY,
    MAIN_AED_COLUMNS,
    MAIN_AED_REQUIRED_SOURCE_COLUMNS,
    MERGE_CONF_NONE,
    POLAND_LAT_RANGE,
    POLAND_LON_RANGE,
    REPORT_CHANGED,
    REPORT_COLUMNS,
    REPORT_MERGED,
    REPORT_NEW,
    REPORT_OK,
    REPORT_REJECTED,
    REPORT_REMOVED,
    REPORT_SKIPPED,
    STALE_DAYS,
)
from mcod.aed.hours import normalize_hours
from mcod.aed.quality import OPTIONAL_FIELDS, anomalies, merge_confidence, trust_score
from mcod.aed.text import normalize_address, text_similarity

logger = logging.getLogger("mcod")


class AEDMissingRequiredColumnError(Exception):
    def __init__(self, column_names: List[str]):
        self.column_names = column_names
        super().__init__("Missing required column(s): " + ", ".join(column_names))


class AEDResourceReadError(Exception):
    """Źródłowy zasób nie może zostać odczytany."""


# --------------------------------------------------------------------------- #
# Czysta logika (pandas)
# --------------------------------------------------------------------------- #


def read_aed_file(file, extension: Optional[str]) -> Optional[pd.DataFrame]:
    """Wczytuje plik xls/xlsx/csv do DataFrame (ponownie używa kodu DGA)."""
    from mcod.resources.dga_utils import create_df_from_dga_file

    return create_df_from_dga_file(file, extension)


def validate_aed_df_columns(df: pd.DataFrame) -> bool:
    """True, jeśli kolumny mają poprawne nazwy i kolejność."""
    return df.columns.to_list() == AED_COLUMNS


def validate_aed_file_columns(file, extension: Optional[str]) -> bool:
    try:
        df = read_aed_file(file, extension)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error reading AED file: %s", exc)
        return False
    if df is None:
        return False
    return validate_aed_df_columns(df)


def _to_float(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def _to_date(value: Any) -> Optional[datetime.date]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return None
    return parsed.date()


def check_row(row: pd.Series) -> Optional[str]:
    """Zwraca opis błędu wiersza lub None, gdy wiersz jest poprawny."""
    for col in MAIN_AED_REQUIRED_SOURCE_COLUMNS:
        value = row.get(col)
        if value is None or (isinstance(value, float) and math.isnan(value)) or str(value).strip() == "":
            return f"brak wartości w kolumnie „{col}”"

    lat, lon = _to_float(row[COL_LAT]), _to_float(row[COL_LON])
    if lat is None or lon is None:
        return "współrzędne nie są liczbami"
    if not (POLAND_LAT_RANGE[0] <= lat <= POLAND_LAT_RANGE[1] and POLAND_LON_RANGE[0] <= lon <= POLAND_LON_RANGE[1]):
        return "współrzędne poza obszarem Polski (kolejność: szerokość, długość; WGS84, kropka dziesiętna)"

    for col, allowed in ENUM_COLUMNS.items():
        if str(row[col]).strip().lower() not in allowed:
            return f"niedozwolona wartość w kolumnie „{col}” (dozwolone: {', '.join(allowed)})"

    if _to_date(row[COL_VERIFIED]) is None:
        return f"niepoprawna data w kolumnie „{COL_VERIFIED}” (format RRRR-MM-DD)"
    return None


def sanitize_source_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Normalizuje wartości i odrzuca niepoprawne wiersze.

    Zwraca (poprawne wiersze, lista odrzuconych z powodem). W odróżnieniu od DGA
    odrzucamy pojedyncze wiersze, a nie cały zasób - jeden błąd dysponenta nie
    blokuje reszty jego danych.
    """
    missing = [c for c in MAIN_AED_REQUIRED_SOURCE_COLUMNS if c not in df.columns]
    if missing:
        raise AEDMissingRequiredColumnError(missing)

    df = df.copy()
    for col in df.columns:
        df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)

    rejected: List[Dict[str, Any]] = []
    keep: List[int] = []
    for idx, row in df.iterrows():
        error = check_row(row)
        if error:
            rejected.append({"row": int(idx) + 2, "id": row.get(COL_ID), "reason": error})
        else:
            keep.append(idx)
    clean = df.loc[keep].copy()
    if not clean.empty:
        clean[COL_LAT] = clean[COL_LAT].map(_to_float)
        clean[COL_LON] = clean[COL_LON].map(_to_float)
        for col in ENUM_COLUMNS:
            clean[col] = clean[col].map(lambda v: str(v).strip().lower())
        clean[COL_VERIFIED] = clean[COL_VERIFIED].map(_to_date)
    clean["_row"] = [int(i) + 2 for i in clean.index]  # numer wiersza w pliku źródłowym (nagłówek = 1), do raportu
    return clean, rejected


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


_STATUS_RANK = {"czynny": 0, "do weryfikacji": 1, "nieczynny": 2}


_UNKNOWN_PROVIDER = "inne źródło"
_GRID_CELL = 0.001  # ok. 110 m: siatka do szybkiego wyszukiwania sąsiadów (promień szukania to maks. 50 m)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def _provider_of(df: pd.DataFrame, i: int) -> str:
    return df.at[i, COL_PROVIDER] if COL_PROVIDER in df.columns else _UNKNOWN_PROVIDER


def _place_similarity(df: pd.DataFrame, i: int, j: int) -> Optional[float]:
    """Podobieństwo miejsca dwóch rekordów (None, gdy nie ma czego porównać).

    Gdy oba rekordy mają adres, decyduje adres: różne budynki z identycznym ogólnikiem w opisie („hol”) to nie to samo
    miejsce. Opis lokalizacji jest używany tylko wtedy, gdy któryś rekord nie ma adresu.
    """
    street = text_similarity(df.at[i, COL_STREET], df.at[j, COL_STREET]) if COL_STREET in df.columns else None
    if street is not None:
        return street
    return text_similarity(df.at[i, COL_LOCATION], df.at[j, COL_LOCATION]) if COL_LOCATION in df.columns else None


def _neighbors(grid: Dict[Tuple[int, int], List[int]], lat: float, lon: float):
    cx, cy = int(lat / _GRID_CELL), int(lon / _GRID_CELL)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            yield from grid.get((cx + dx, cy + dy), [])


def _match(df: pd.DataFrame, i: int, j: int, certain_m: float, max_m: float) -> Optional[Tuple[float, int]]:
    """(odległość, pewność) gdy rekordy i, j to to samo urządzenie, inaczej None.

    Do ``certain_m`` łączymy zawsze; do ``max_m`` tylko gdy opisy miejsca są podobne.
    """
    distance = haversine_m(df.at[i, COL_LAT], df.at[i, COL_LON], df.at[j, COL_LAT], df.at[j, COL_LON])
    if distance > max_m:
        return None
    similarity = _place_similarity(df, i, j)
    if distance > certain_m and (similarity is None or similarity < DEDUP_TEXT_MIN):
        return None
    return distance, merge_confidence(distance, similarity, max_m)


def _find_duplicate(df, grid, i: int, certain_m: float, max_m: float) -> Optional[Tuple[int, float, int]]:
    """Najpewniejszy wcześniej zachowany rekord INNEGO dysponenta: (indeks, odległość, pewność) albo None."""
    best = None
    for j in _neighbors(grid, df.at[i, COL_LAT], df.at[i, COL_LON]):
        if COL_PROVIDER in df.columns and df.at[j, COL_PROVIDER] == df.at[i, COL_PROVIDER]:
            continue
        found = _match(df, i, j, certain_m, max_m)
        if found and (best is None or (found[1], -found[0]) > (best[2], -best[1])):
            best = (j, found[0], found[1])
    return best


def _merge_log_entry(df: pd.DataFrame, merged_index: int, winner_index: int, distance: float, confidence: int) -> Dict[str, Any]:
    return {
        "provider": _provider_of(df, merged_index),
        "resource": df.at[merged_index, COL_SOURCE_RESOURCE] if COL_SOURCE_RESOURCE in df.columns else None,
        "row": df.at[merged_index, "_row"] if "_row" in df.columns else None,
        "id": df.at[merged_index, COL_ID],
        "winner_provider": _provider_of(df, winner_index),
        "winner_id": df.at[winner_index, COL_ID],
        "distance": distance,
        "confidence": confidence,
    }


def _filled_optional_fields(row: pd.Series) -> int:
    return sum(1 for f in OPTIONAL_FIELDS if f in row.index and not _is_blank(row[f]))


def deduplicate(
    df: pd.DataFrame,
    certain_m: float = DEDUP_CERTAIN_METERS,
    max_m: float = DEDUP_MAX_METERS,
    merge_log: Optional[List[Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """Usuwa duplikaty: to samo urządzenie zgłoszone przez kilku dysponentów.

    Rekordy różnych dysponentów łączymy, gdy leżą bliżej niż ``certain_m`` albo (do ``max_m``) mają podobny adres
    lub opis miejsca; różne numery budynków nigdy nie są „podobne”. Z grupy zostaje rekord najlepszy: status „czynny”,
    najświeższa weryfikacja, najpełniejszy opis. Dwa urządzenia jednego dysponenta to dwa urządzenia.
    Dopisuje „Liczba źródeł”, „Pozostali dysponenci” i „Pewność połączenia” (najniższa z połączeń).
    """
    df = df.copy()
    if df.empty:
        df[COL_SOURCES_COUNT] = pd.Series(dtype=int)
        df[COL_OTHER_PROVIDERS] = pd.Series(dtype=object)
        df[COL_MERGE_CONF] = pd.Series(dtype=object)
        return df

    df["_rank"] = df[COL_STATUS].map(_STATUS_RANK).fillna(3)
    df["_ver"] = df[COL_VERIFIED].map(lambda d: d.toordinal() if d else 0)
    df["_cmp"] = df.apply(_filled_optional_fields, axis=1)
    df = df.sort_values(["_rank", "_ver", "_cmp"], ascending=[True, False, False]).reset_index(drop=True)

    grid: Dict[Tuple[int, int], List[int]] = {}
    merged: Dict[int, List[Tuple[int, float, int]]] = {}  # zachowany rekord -> [(dołączony, odległość, pewność)]
    for i in df.index:
        winner = _find_duplicate(df, grid, i, certain_m, max_m)
        if winner is None:
            grid.setdefault((int(df.at[i, COL_LAT] / _GRID_CELL), int(df.at[i, COL_LON] / _GRID_CELL)), []).append(i)
            merged[i] = []
        else:
            merged[winner[0]].append((i, winner[1], winner[2]))

    if merge_log is not None:
        merge_log.extend(_merge_log_entry(df, j, i, d, c) for i, members in merged.items() for j, d, c in members)

    def others(i: int) -> Optional[str]:
        parts = [f"{_provider_of(df, j)} ({df.at[j, COL_ID]})" for j, _, _ in merged[i]]
        return "; ".join(parts) if parts else None

    kept = list(merged)
    result = df.loc[kept].copy()
    result[COL_SOURCES_COUNT] = [1 + len(merged[i]) for i in kept]
    result[COL_OTHER_PROVIDERS] = [others(i) for i in kept]
    lowest = [min((c for _, _, c in merged[i]), default=None) for i in kept]
    result[COL_MERGE_CONF] = [f"{c}%" if c is not None else MERGE_CONF_NONE for c in lowest]
    return result.drop(columns=["_rank", "_ver", "_cmp"])


def compute_freshness(
    verified: Optional[datetime.date], status: str, today: Optional[datetime.date] = None
) -> Tuple[str, Optional[int]]:
    """Aktualność rekordu na podstawie statusu i daty ostatniej weryfikacji.

    nieczynny        - status „nieczynny” (urządzenie nie nadaje się do użycia),
    nieaktualny      - weryfikacja starsza niż 2 lata,
    do weryfikacji   - status „do weryfikacji”, weryfikacja starsza niż rok albo data z przyszłości,
    aktualny         - czynny i zweryfikowany w ciągu ostatniego roku.
    Zwraca (aktualność, liczba dni od weryfikacji).
    """
    today = today or datetime.date.today()
    if not verified:
        return FRESHNESS_TO_VERIFY, None
    days = (today - verified).days
    if status == "nieczynny":
        return FRESHNESS_BROKEN, days
    if days > STALE_DAYS:
        return FRESHNESS_STALE, days
    if days < 0 or days > FRESH_DAYS or status == "do weryfikacji":
        return FRESHNESS_TO_VERIFY, days
    return FRESHNESS_ACTUAL, days


def _report_row(provider, resource_id, row, aed_id, result, reason) -> Dict[str, Any]:
    return dict(zip(REPORT_COLUMNS, [provider, resource_id, row, aed_id, result, reason]))


def build_report_df(report: List[Dict[str, Any]]) -> pd.DataFrame:
    """Raport scalania jako tabela. Gdy uwag nie ma, jedna wiersz „brak uwag” (pusty plik nie przechodzi walidacji portalu)."""
    if not report:
        report = [_report_row("", None, None, "", REPORT_OK, "wszystkie wykazy przetworzone bez zastrzeżeń")]
    df = pd.DataFrame(report, columns=REPORT_COLUMNS)
    df["Wiersz w pliku"] = pd.array(df["Wiersz w pliku"].tolist(), dtype="Int64")
    df["Zasób źródłowy"] = pd.array(df["Zasób źródłowy"].tolist(), dtype="Int64")
    return df


def enrich_source_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ujednolica adresy i godziny wykazu jednego dysponenta (przed scaleniem)."""
    df = df.copy()
    addresses = [normalize_address(street, city) for street, city in zip(df[COL_STREET], df[COL_CITY])]
    df[COL_STREET] = [a.street for a in addresses]
    df[COL_CITY] = [a.city for a in addresses]
    df[COL_POSTAL] = [a.postal for a in addresses]
    hours = [normalize_hours(h, avail) for h, avail in zip(df[COL_HOURS], df[COL_AVAILABILITY])]
    df[COL_HOURS_NORM] = hours
    df["_hours_unparsed"] = [h is None and not _is_blank(raw) for h, raw in zip(hours, df[COL_HOURS])]
    return df


def _collect_frames(sources, report: Optional[List[Dict[str, Any]]]) -> List[pd.DataFrame]:
    frames = []
    for df, meta in sources:
        clean, rejected = sanitize_source_df(df)
        for item in rejected:
            logger.warning("AED source %s: row %s rejected: %s", meta.get("resource_id"), item["row"], item["reason"])
            if report is not None:
                report.append(
                    _report_row(
                        meta["provider"], meta.get("resource_id"), item["row"], item["id"], REPORT_REJECTED, item["reason"]
                    )
                )
        if clean.empty:
            continue
        clean = enrich_source_df(clean)
        clean[COL_PROVIDER] = meta["provider"]
        clean[COL_SCOPE] = meta["scope"]
        clean[COL_SOURCE_RESOURCE] = meta["resource_id"]
        clean[COL_SOURCE_DATE] = meta.get("data_date")
        frames.append(clean)
    return frames


def _apply_quality(df: pd.DataFrame) -> None:
    """Dopisuje „Uwagi do danych” (flagi anomalii) i „Wiarygodność” (0-100)."""
    notes_column, trust_column = [], []
    for _, row in df.iterrows():
        notes = anomalies(row, int(row["_same_point"]), bool(row["_hours_unparsed"]))
        notes_column.append("; ".join(notes) or None)
        trust_column.append(trust_score(row, len(notes)))
    df[COL_NOTES] = notes_column
    df[COL_TRUST] = pd.array(trust_column, dtype="Int64")


def _merge_report_rows(merge_log: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for m in merge_log:
        reason = (
            f"ten sam punkt co {m['winner_id']} ({m['winner_provider']}): odległość {m['distance']:.0f} m, "
            f"pewność {m['confidence']}%; w wykazie zbiorczym zostaje tamten rekord"
        )
        rows.append(_report_row(m["provider"], m["resource"], m["row"], m["id"], REPORT_MERGED, reason))
    return rows


def build_main_df(
    sources: List[Tuple[pd.DataFrame, Dict[str, Any]]],
    today: Optional[datetime.date] = None,
    report: Optional[List[Dict[str, Any]]] = None,
) -> pd.DataFrame:
    """Scala wykazy dostawców w jeden zbiorczy wykaz.

    ``sources`` - lista par (DataFrame wykazu, metadane: provider, scope, resource_id, data_date).
    Kolejność: walidacja wierszy, ujednolicenie adresów i godzin, deduplikacja, aktualność, wiarygodność.
    """
    frames = _collect_frames(sources, report)
    if not frames:
        return pd.DataFrame(columns=MAIN_AED_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    combined["_same_point"] = combined.groupby([COL_PROVIDER, COL_LAT, COL_LON])[COL_ID].transform("count")
    merge_log: List[Dict[str, Any]] = []
    main_df = deduplicate(combined, merge_log=merge_log)
    if report is not None:
        report.extend(_merge_report_rows(merge_log))
    main_df = main_df.sort_values([COL_PROVIDER, COL_ID]).reset_index(drop=True)
    main_df["Lp."] = range(1, len(main_df) + 1)
    fresh = [compute_freshness(v, st, today) for v, st in zip(main_df[COL_VERIFIED], main_df[COL_STATUS])]
    main_df[COL_FRESHNESS] = [f[0] for f in fresh]
    main_df[COL_DAYS_SINCE] = pd.array([f[1] for f in fresh], dtype="Int64")
    _apply_quality(main_df)
    return main_df.reindex(columns=MAIN_AED_COLUMNS)


def main_df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8", date_format="%Y-%m-%d")
    return buf.getvalue()


def _json_value(v: Any) -> Any:
    if v is None or (not isinstance(v, (list, dict)) and pd.isna(v)):
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "item"):  # skalary numpy (np.int64 itp.) nie są serializowalne do JSON
        return v.item()
    return v


def main_df_to_geojson(df: pd.DataFrame) -> Dict[str, Any]:
    features = []
    for _, row in df.iterrows():
        props = {k: _json_value(v) for k, v in row.items() if k not in (COL_LAT, COL_LON)}
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(row[COL_LON]), float(row[COL_LAT])]},
                "properties": props,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def apply_aed_geo_schema(tds: Dict[str, Any]) -> Dict[str, Any]:
    """Dopisuje do schematu tabelarycznego mapowanie kolumn na mapę portalu.

    Portal rysuje mapę dla zasobów, których schemat ma ``geo`` z elementami
    ``b`` (szerokość), ``l`` (długość) i ``label`` (opis punktu) - normalnie dostawca
    ustawia to ręcznie w zakładce „Mapy i wykresy”. Układ kolumn wykazu AED jest
    stały, więc robimy to automatycznie. Funkcja jest idempotentna.
    """
    from mcod.aed.constants import COL_LABEL_FOR_MAP

    if not tds or "fields" not in tds:
        return tds
    wanted = {COL_LAT: "b", COL_LON: "l", COL_LABEL_FOR_MAP: "label"}
    geo: Dict[str, Any] = {}
    for index, field in enumerate(tds["fields"]):
        key = wanted.get(field.get("name"))
        if key:
            field["geo"] = key
            geo[key] = {"col_name": field["name"], "col_index": index}
        elif "geo" in field:
            del field["geo"]
    if {"b", "l", "label"} <= set(geo):
        tds["geo"] = geo
    return tds


# --------------------------------------------------------------------------- #
# Część bazodanowa
# --------------------------------------------------------------------------- #


AED_REMOTE_NO_URL = "no_url"
AED_REMOTE_NOT_ACCESSIBLE = "not_accessible"
AED_REMOTE_BAD_EXTENSION = "bad_extension"
AED_REMOTE_BAD_COLUMNS = "bad_columns"


def check_remote_aed_file(url: Optional[str]) -> Optional[str]:
    """Sprawdza zdalny plik wykazu AED (import XML i CKAN) tymi samymi regułami co formularz w panelu.

    Zwraca kod błędu (stałe AED_REMOTE_*) albo None, gdy plik jest poprawny: adres odpowiada (200),
    to csv/xls/xlsx, a kolumny mają nazwy i kolejność wzorca. Odpowiednik walidacji wykazu DGA.
    """
    import requests

    from mcod.resources.dga_utils import (
        create_df_from_dga_file,
        get_remote_extension_if_correct_dga_content_type,
        request_remote_dga,
    )

    if not url:
        return AED_REMOTE_NO_URL
    try:
        response = request_remote_dga(url)
    except requests.exceptions.RequestException:
        return AED_REMOTE_NOT_ACCESSIBLE
    if response.status_code != 200:
        return AED_REMOTE_NOT_ACCESSIBLE
    extension = get_remote_extension_if_correct_dga_content_type(response)
    if extension is None:
        return AED_REMOTE_BAD_EXTENSION
    try:
        df = create_df_from_dga_file(BytesIO(response.content), extension)
    except Exception:  # noqa: BLE001
        return AED_REMOTE_BAD_COLUMNS
    if df is None or not validate_aed_df_columns(df):
        return AED_REMOTE_BAD_COLUMNS
    return None


AED_REMOTE_MESSAGES = {
    AED_REMOTE_NO_URL: "Wykaz AED musi wskazywać plik w polu 'url'.",
    AED_REMOTE_NOT_ACCESSIBLE: "Adres w polu 'url' wykazu AED nie odpowiada.",
    AED_REMOTE_BAD_EXTENSION: "Wykaz AED musi wskazywać plik w formacie xls, xlsx lub csv.",
    AED_REMOTE_BAD_COLUMNS: "Plik wykazu AED musi zawierać dokładnie %d kolumn ułożonych i nazwanych dokładnie: %s."
    % (len(AED_COLUMNS), ", ".join(AED_COLUMNS)),
}


def get_main_aed_resource():
    from mcod.aed.models import AggregatedAEDInfo

    info = AggregatedAEDInfo.objects.last()
    return info.main_aed_resource if info else None


def get_aed_resource_for_institution(organization_id, exclude_resource_id=None):
    """Zasób-wykaz AED danej instytucji (maks. jeden, jak w DGA)."""
    from mcod.resources.models import Resource

    exclude = [pk for pk in (exclude_resource_id,) if pk]
    main = get_main_aed_resource()
    if main:
        exclude.append(main.pk)
    query = Resource.objects.filter(
        dataset__organization=organization_id,
        contains_aed_list=True,
        status="published",
    ).exclude(id__in=exclude)
    if query.count() > 1:
        from django.core.exceptions import MultipleObjectsReturned

        raise MultipleObjectsReturned(f"Found more than one AED resource for organization {organization_id}")
    return query.first()


def get_source_resources():
    """Wszystkie opublikowane wykazy AED dostawców (bez zbiorczego), także jeszcze niezwalidowane."""
    from mcod.resources.models import Resource

    main = get_main_aed_resource()
    qs = Resource.objects.filter(contains_aed_list=True, status="published")
    if main:
        qs = qs.exclude(id=main.pk)
    return qs.select_related("dataset__organization").order_by("dataset__organization__title")


def _validation_ok(resource) -> bool:
    return all(
        st == "SUCCESS"
        for st in (resource.data_tasks_last_status, resource.file_tasks_last_status, resource.link_tasks_last_status)
    )


def read_source_df(resource) -> pd.DataFrame:
    """Wczytuje wykaz dostawcy z pliku zasobu."""
    main_file = resource.main_file
    if not main_file:
        raise AEDResourceReadError(f"Resource {resource.pk} has no file")
    extension = os.path.splitext(main_file.path)[1].lstrip(".").lower()
    try:
        with open(main_file.path, "rb") as fh:
            df = read_aed_file(BytesIO(fh.read()), extension)
    except Exception as exc:  # noqa: BLE001
        raise AEDResourceReadError(f"Cannot read resource {resource.pk}: {exc}") from exc
    if df is None:
        raise AEDResourceReadError(f"Cannot parse resource {resource.pk}")
    return df


def collect_sources(report: Optional[List[Dict[str, Any]]] = None) -> List[Tuple[pd.DataFrame, Dict[str, Any]]]:
    from django.conf import settings

    def skip(resource, reason):
        logger.error("Skipping AED source %s: %s", resource.pk, reason)
        if report is not None:
            report.append(_report_row(resource.dataset.organization.title, resource.pk, None, "", REPORT_SKIPPED, reason))

    sources = []
    for resource in get_source_resources():
        if getattr(settings, "AED_REQUIRE_VALIDATED_SOURCES", True) and not _validation_ok(resource):
            skip(
                resource,
                "walidacja zasobu w portalu trwa albo się nie powiodła (dane: %s, plik: %s, link: %s); popraw plik lub poczekaj"
                % (resource.data_tasks_last_status, resource.file_tasks_last_status, resource.link_tasks_last_status),
            )
            continue
        try:
            df = read_source_df(resource)
        except AEDResourceReadError as exc:
            skip(resource, f"nie udało się odczytać pliku ({exc})")
            continue
        if not validate_aed_df_columns(df):
            skip(resource, "nazwy lub kolejność kolumn różnią się od wzorca: " + ", ".join(AED_COLUMNS))
            continue
        sources.append(
            (
                df,
                {
                    "provider": resource.dataset.organization.title,
                    "scope": resource.title,
                    "resource_id": resource.pk,
                    "data_date": resource.data_date,
                },
            )
        )
    return sources


@dataclass
class AEDBuild:
    main_df: pd.DataFrame
    report: List[Dict[str, Any]]
    csv_path: Path


def read_previous_main_df() -> Optional[pd.DataFrame]:
    """Poprzedni wykaz zbiorczy (plik obecnego zasobu), do wykrywania zmian. None przy pierwszym scaleniu."""
    resource = get_main_aed_resource()
    if resource is None or not resource.main_file:
        return None
    try:
        return pd.read_csv(resource.main_file.path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cannot read previous main AED file: %s", exc)
        return None


def build_main_aed(directory: Optional[Path] = None) -> AEDBuild:
    """Scala wykazy dostawców: zwraca tabelę zbiorczą, raport uwag i ścieżkę pliku CSV."""
    from django.conf import settings

    directory = Path(directory or settings.MAIN_AED_RESOURCE_CREATION_ROOT)
    directory.mkdir(parents=True, exist_ok=True)
    report: List[Dict[str, Any]] = []
    sources = collect_sources(report)
    main_df = build_main_df(sources, report=report)
    report.extend(diff_main(read_previous_main_df(), main_df))
    path = directory / f"{settings.MAIN_AED_FILE_NAME_PREFIX} {datetime.datetime.now():%Y%m%d}.csv"
    path.write_bytes(main_df_to_csv_bytes(main_df))
    return AEDBuild(main_df=main_df, report=report, csv_path=path)


def create_main_aed_file(directory: Optional[Path] = None) -> Path:
    return build_main_aed(directory).csv_path


def ensure_main_dataset_license(dataset):
    """Zbiór zbiorczy jest na licencji CC BY 4.0 (uznanie autorstwa), niezależnie od tego, kiedy powstał."""
    from mcod.datasets.models import Dataset

    if dataset.license_chosen != Dataset.LICENSE_CC_BY or not dataset.license_condition_default_cc40:
        dataset.license_chosen = Dataset.LICENSE_CC_BY
        dataset.license_condition_default_cc40 = True
        dataset.save()
    return dataset


def _get_or_create_main_dataset():
    from django.apps import apps
    from django.conf import settings
    from django.db import transaction

    from mcod.aed.models import AggregatedAEDInfo

    info = AggregatedAEDInfo.objects.last()
    if info and info.main_aed_dataset:
        return ensure_main_dataset_license(info.main_aed_dataset)

    Organization = apps.get_model("organizations", "Organization")
    Dataset = apps.get_model("datasets", "Dataset")
    Category = apps.get_model("categories", "Category")
    Tag = apps.get_model("tags", "Tag")
    # właściciel zbioru zbiorczego: po pk (jak w DGA), a gdy go brak - po nazwie (środowiska lokalne/demo)
    owner = Organization.objects.filter(pk=settings.MAIN_AED_DATASET_OWNER_ORGANIZATION_PK).first()
    if owner is None:
        owner = Organization.objects.get(title=settings.MAIN_AED_DATASET_OWNER_ORGANIZATION_TITLE)
    with transaction.atomic():
        dataset = Dataset.objects.create(
            title=settings.MAIN_AED_DATASET_DEFAULT_TITLE,
            notes=settings.MAIN_AED_DATASET_DEFAULT_DESC,
            organization=owner,
            update_notification_recipient_email=settings.MAIN_AED_DATASET_UPDATE_NOTIFICATION_EMAIL,
            has_dynamic_data=True,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            update_frequency="daily",
            status="published",
            license_chosen=Dataset.LICENSE_CC_BY,
            license_condition_default_cc40=True,
        )
        dataset.categories.set(Category.objects.filter(title__in=settings.MAIN_AED_DATASET_CATEGORIES_TITLES))
        tags = [Tag.objects.get_or_create(name=n, language="pl")[0] for n in settings.MAIN_AED_DATASET_TAGS_NAMES]
        dataset.tags.set(tags)
        dataset.save()
    return dataset


def create_or_update_main_aed_resource(file_path: Path):
    """Zasób zbiorczy: pierwszy raz tworzy, potem AKTUALIZUJE w miejscu (ten sam id i adres).

    Wzorzec z panelu administracyjnego: ``update_or_create`` pliku głównego i ``revalidate()``, który
    ponownie przetwarza dane, schemat mapy i indeks w Elasticsearch. W przeciwieństwie do wykazu DGA nie usuwamy
    starego zasobu, więc linki, zakładki i zasilanie z zewnątrz nie psują się po każdym scaleniu.
    """
    from django.conf import settings
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import transaction

    from mcod.aed.models import AggregatedAEDInfo
    from mcod.resources.models import Resource, ResourceFile

    upload = SimpleUploadedFile(
        name=f"{settings.MAIN_AED_FILE_NAME_PREFIX}.csv",  # stała nazwa pliku, bez daty
        content=file_path.read_bytes(),
        content_type="text/csv",
    )
    existing = get_main_aed_resource()
    if existing is not None:
        with transaction.atomic():
            existing.data_date = datetime.date.today()
            existing.tabular_data_schema = None  # schemat (typy kolumn i mapa) zostanie wyliczony na nowo z aktualnego pliku
            existing.save()
            ResourceFile.objects.update_or_create(resource=existing, is_main=True, defaults={"file": upload})
        existing.revalidate()
        return existing

    with transaction.atomic():
        dataset = _get_or_create_main_dataset()
        resource = Resource.objects.create(
            title=settings.MAIN_AED_RESOURCE_DEFAULT_TITLE,
            description=settings.MAIN_AED_RESOURCE_DEFAULT_DESC,
            dataset=dataset,
            has_dynamic_data=True,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            contains_aed_list=True,
            status="published",
            data_date=datetime.date.today(),
        )
        ResourceFile.objects.create(resource=resource, is_main=True, file=upload)  # post_save uruchamia walidację
        info = AggregatedAEDInfo.objects.last()
        if info:
            info.resource = resource
            info.save()
        else:
            AggregatedAEDInfo.objects.create(resource=resource)
    return resource


# zgodność wsteczna nazwy
create_main_aed_resource = create_or_update_main_aed_resource


def merge_summary(build: AEDBuild) -> str:
    """Jedno zdanie o ostatnim scaleniu (trafia do opisu zasobu z raportem)."""
    counts: Dict[str, int] = {}
    for r in build.report:
        counts[r["Wynik"]] = counts.get(r["Wynik"], 0) + 1
    providers = build.main_df["Nazwa dysponenta zasobu"].nunique() if not build.main_df.empty else 0
    return (
        f"Ostatnie scalenie: {datetime.date.today():%Y-%m-%d}. Rekordów w wykazie zbiorczym: {len(build.main_df)} "
        f"(dysponentów z danymi: {providers}). Odrzuconych wierszy: {counts.get(REPORT_REJECTED, 0)}, "
        f"połączonych duplikatów: {counts.get(REPORT_MERGED, 0)}, pominiętych zasobów: {counts.get(REPORT_SKIPPED, 0)}. "
        f"Zmiany od poprzedniego scalenia: nowych {counts.get(REPORT_NEW, 0)}, usuniętych {counts.get(REPORT_REMOVED, 0)}, "
        f"zmienionych {counts.get(REPORT_CHANGED, 0)}. "
        "Każdy wiersz raportu opisuje jedną uwagę do wykazu dostawcy: poprawcie plik i scalenie uwzględni zmiany następnego dnia."
    )


def upsert_auxiliary_resource(dataset, title: str, description: str, filename: str, content: bytes, content_type: str):
    """Zasób pomocniczy zbioru zbiorczego (raport, GeoJSON): tworzony raz, potem aktualizowany w miejscu.

    Nie jest wykazem dostawcy (contains_aed_list=False), więc nie bierze udziału w scalaniu.
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import transaction

    from mcod.resources.models import Resource, ResourceFile

    upload = SimpleUploadedFile(name=filename, content=content, content_type=content_type)
    existing = Resource.objects.filter(dataset=dataset, title=title, contains_aed_list=False).first()
    if existing is not None:
        with transaction.atomic():
            existing.description = description
            existing.data_date = datetime.date.today()
            existing.tabular_data_schema = None
            existing.save()
            ResourceFile.objects.update_or_create(resource=existing, is_main=True, defaults={"file": upload})
        existing.revalidate()
        return existing
    with transaction.atomic():
        resource = Resource.objects.create(
            title=title,
            description=description,
            dataset=dataset,
            has_dynamic_data=True,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            contains_aed_list=False,
            status="published",
            data_date=datetime.date.today(),
        )
        ResourceFile.objects.create(resource=resource, is_main=True, file=upload)
    return resource


def publish_auxiliary_resources(dataset, build: AEDBuild) -> Dict[str, Any]:
    """Raport scalania (CSV) i GeoJSON obok zasobu zbiorczego."""
    from django.conf import settings

    report_csv = main_df_to_csv_bytes(build_report_df(build.report))
    report = upsert_auxiliary_resource(
        dataset,
        settings.MAIN_AED_REPORT_RESOURCE_TITLE,
        merge_summary(build),
        "Raport_scalania_AED.csv",
        report_csv,
        "text/csv",
    )
    geojson = upsert_auxiliary_resource(
        dataset,
        settings.MAIN_AED_GEOJSON_RESOURCE_TITLE,
        settings.MAIN_AED_GEOJSON_RESOURCE_DESC,
        "Wykaz_AED_zbiorczy.geojson",
        json.dumps(main_df_to_geojson(build.main_df), ensure_ascii=False).encode("utf-8"),
        "application/geo+json",
    )
    return {"report": report, "geojson": geojson}


def run_main_aed_build():
    """Pełny przebieg: scalenie, zasób zbiorczy (w miejscu), raport i GeoJSON. Wspólny dla zadania Celery i komendy."""
    build = build_main_aed()
    main = create_or_update_main_aed_resource(build.csv_path)
    aux = publish_auxiliary_resources(main.dataset, build)
    return main, aux, build

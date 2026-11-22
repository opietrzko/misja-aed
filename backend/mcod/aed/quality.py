"""Wiarygodność rekordu (0-100) i flagi anomalii.

Jawne, wyjaśnialne reguły, bez uczenia maszynowego. Wagi i progi to **nasze założenia** do dostrojenia, nie wiedza
ekspercka. Wiarygodność mówi, na ile można polegać na rekordzie jako na pomocy: czy urządzenie istnieje, jest
aktualne, dobrze opisane i potwierdzone przez niezależne źródła.

Punkty (suma 100):
  kompletność opisu          do 30  (udział wypełnionych pól opcjonalnych)
  aktualność weryfikacji     do 30  (im świeższa, tym więcej; „do weryfikacji” liczy się w połowie)
  potwierdzenie przez inne źródła  do 20  (2 dysponentów = 15, 3 i więcej = 20)
  dokładność współrzędnych   do 10  (5+ miejsc po przecinku = 10, 4 = 7, 3 = 3)
  godziny w zapisie maszynowym    do 10  (rozpoznane godziny albo 24/7)
Od wyniku odejmujemy 10 punktów za każdą flagę anomalii. Urządzenie „nieczynne” nie dostaje więcej niż 20.
"""

import math
from typing import Any, List, Optional

import pandas as pd

from mcod.aed.constants import (
    COL_AVAILABILITY,
    COL_CITY,
    COL_CONTACT,
    COL_DAYS_SINCE,
    COL_HOURS_NORM,
    COL_LAT,
    COL_LOCATION,
    COL_LON,
    COL_OBJECT_TYPE,
    COL_SOURCES_COUNT,
    COL_STATUS,
    COL_STREET,
    COL_TERYT,
)

COMPLETENESS_MAX = 30
FRESHNESS_MAX = 30
PRECISION_MAX = 10
HOURS_MAX = 10
BROKEN_CAP = 20
ANOMALY_PENALTY = 10
SAME_POINT_THRESHOLD = 3  # tyle rekordów jednego dysponenta w identycznym punkcie to podejrzany „środek miasta”

OPTIONAL_FIELDS = [COL_CITY, COL_STREET, COL_TERYT, COL_LOCATION, COL_OBJECT_TYPE, COL_CONTACT]


def _blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def coordinate_decimals(value: Any) -> int:
    """Liczba miejsc po przecinku (ponad 7 traktujemy jako artefakt zmiennoprzecinkowy)."""
    if _blank(value):
        return 0
    text = repr(round(float(value), 7))
    return len(text.split(".")[1].rstrip("0")) if "." in text else 0


def completeness_points(row: pd.Series) -> int:
    fields = list(OPTIONAL_FIELDS)
    if row.get(COL_AVAILABILITY) == "w godzinach":
        fields.append(COL_HOURS_NORM)  # dla „w godzinach” godziny też należą do opisu
    filled = sum(1 for f in fields if not _blank(row.get(f)))
    return round(COMPLETENESS_MAX * filled / len(fields))


def freshness_points(days: Any, status: Any) -> int:
    if _blank(days):
        return 0
    days = int(days)
    if days < 0:
        points = 5  # data z przyszłości jest podejrzana
    elif days <= 180:
        points = FRESHNESS_MAX
    elif days <= 365:
        points = 22
    elif days <= 730:
        points = 10
    else:
        points = 0
    return points // 2 if status == "do weryfikacji" else points


def corroboration_points(sources: Any) -> int:
    n = 1 if _blank(sources) else int(sources)
    return 0 if n <= 1 else (15 if n == 2 else 20)


def precision_points(lat: Any, lon: Any) -> int:
    digits = min(coordinate_decimals(lat), coordinate_decimals(lon))
    return 10 if digits >= 5 else 7 if digits == 4 else 3 if digits == 3 else 0


def hours_points(row: pd.Series) -> int:
    return HOURS_MAX if not _blank(row.get(COL_HOURS_NORM)) else 0


def anomalies(row: pd.Series, same_point_count: int = 1, hours_unparsed: bool = False) -> List[str]:
    """Flagi anomalii danych (każda odejmuje punkty wiarygodności)."""
    notes: List[str] = []
    digits = min(coordinate_decimals(row.get(COL_LAT)), coordinate_decimals(row.get(COL_LON)))
    if digits <= 2:
        notes.append("bardzo niska precyzja współrzędnych (ok. 1 km)")
    elif digits == 3:
        notes.append("niska precyzja współrzędnych (ok. 100 m)")
    if same_point_count >= SAME_POINT_THRESHOLD:
        notes.append(f"identyczne współrzędne w {same_point_count} rekordach dysponenta")
    days = row.get(COL_DAYS_SINCE)
    if not _blank(days) and int(days) < 0:
        notes.append("data weryfikacji z przyszłości")
    if hours_unparsed:
        notes.append("godziny nie zostały rozpoznane (zostaje tekst źródłowy)")
    return notes


def trust_score(row: pd.Series, anomaly_count: int = 0) -> int:
    corroboration = corroboration_points(row.get(COL_SOURCES_COUNT))
    score = (
        completeness_points(row)
        + freshness_points(row.get(COL_DAYS_SINCE), row.get(COL_STATUS))
        + corroboration
        + precision_points(row.get(COL_LAT), row.get(COL_LON))
        + hours_points(row)
    )
    score -= ANOMALY_PENALTY * anomaly_count
    if row.get(COL_STATUS) == "nieczynny":
        score = min(score, BROKEN_CAP)
    return max(0, min(100, int(score)))


def merge_confidence(distance_m: float, similarity: Optional[float], max_m: float) -> int:
    """Pewność połączenia dwóch rekordów (0-100) z odległości i podobieństwa opisów miejsca."""
    distance_score = 1.0 if distance_m <= 3 else max(0.0, 1 - (distance_m - 3) / (max_m - 3))
    if similarity is None:
        combined = distance_score
    else:
        combined = 0.6 * distance_score + 0.4 * similarity
    if math.isnan(combined):
        return 0
    return int(round(100 * min(1.0, combined)))

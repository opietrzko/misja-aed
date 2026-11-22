"""Logika wykazu AED - odpowiednik mcod.resources.dga_utils dla defibrylatorów.

Część "czysta" (pandas) nie dotyka bazy danych, dzięki czemu jest testowalna
bez środowiska Django. Część "bazodanowa" (zasoby, zbiór danych) jest
na końcu pliku.
"""

import datetime
import logging
import math
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from mcod.aed.constants import (
    AED_COLUMNS,
    COL_ACCESS,
    COL_AVAILABILITY,
    COL_ID,
    COL_LAT,
    COL_LON,
    COL_PROVIDER,
    COL_SCOPE,
    COL_SOURCE_DATE,
    COL_SOURCE_RESOURCE,
    COL_STATUS,
    COL_VERIFIED,
    DEDUP_DISTANCE_METERS,
    ENUM_COLUMNS,
    MAIN_AED_COLUMNS,
    MAIN_AED_REQUIRED_SOURCE_COLUMNS,
    POLAND_LAT_RANGE,
    POLAND_LON_RANGE,
)

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
    return clean, rejected


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


_STATUS_RANK = {"czynny": 0, "do weryfikacji": 1, "nieczynny": 2}


def deduplicate(df: pd.DataFrame, distance_m: float = DEDUP_DISTANCE_METERS) -> pd.DataFrame:
    """Usuwa duplikaty - ten sam AED zgłoszony przez kilku dysponentów.

    Z grupy punktów leżących bliżej niż ``distance_m`` zostaje rekord najlepszy:
    status „czynny”, potem najświeższa weryfikacja. Dopisuje kolumnę
    „Liczba źródeł” z liczbą połączonych rekordów.
    """
    if df.empty:
        df = df.copy()
        df["Liczba źródeł"] = pd.Series(dtype=int)
        return df

    df = df.copy()
    df["_rank"] = df[COL_STATUS].map(_STATUS_RANK).fillna(3)
    df["_ver"] = df[COL_VERIFIED].map(lambda d: d.toordinal() if d else 0)
    df = df.sort_values(["_rank", "_ver"], ascending=[True, False]).reset_index(drop=True)

    cell = 0.001  # ~110 m: siatka do szybkiego wyszukiwania sąsiadów
    grid: Dict[Tuple[int, int], List[int]] = {}
    kept: List[int] = []
    counts: Dict[int, int] = {}
    for i, row in df.iterrows():
        lat, lon = row[COL_LAT], row[COL_LON]
        cx, cy = int(lat / cell), int(lon / cell)
        match = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx + dx, cy + dy), []):
                    if haversine_m(lat, lon, df.at[j, COL_LAT], df.at[j, COL_LON]) <= distance_m:
                        match = j
                        break
                if match is not None:
                    break
            if match is not None:
                break
        if match is None:
            grid.setdefault((cx, cy), []).append(i)
            kept.append(i)
            counts[i] = 1
        else:
            counts[match] += 1
    result = df.loc[kept].copy()
    result["Liczba źródeł"] = [counts[i] for i in kept]
    return result.drop(columns=["_rank", "_ver"])


def build_main_df(sources: List[Tuple[pd.DataFrame, Dict[str, Any]]]) -> pd.DataFrame:
    """Scala wykazy dostawców w jeden zbiorczy wykaz.

    ``sources`` - lista par (DataFrame wykazu, metadane: provider, scope, resource_id, data_date).
    """
    frames = []
    for df, meta in sources:
        clean, rejected = sanitize_source_df(df)
        for item in rejected:
            logger.warning("AED source %s: row %s rejected: %s", meta.get("resource_id"), item["row"], item["reason"])
        if clean.empty:
            continue
        clean[COL_PROVIDER] = meta["provider"]
        clean[COL_SCOPE] = meta["scope"]
        clean[COL_SOURCE_RESOURCE] = meta["resource_id"]
        clean[COL_SOURCE_DATE] = meta.get("data_date")
        frames.append(clean)

    if not frames:
        main_df = pd.DataFrame(columns=MAIN_AED_COLUMNS + ["Liczba źródeł"])
    else:
        main_df = deduplicate(pd.concat(frames, ignore_index=True))
        main_df = main_df.sort_values([COL_PROVIDER, COL_ID]).reset_index(drop=True)
        main_df["Lp."] = range(1, len(main_df) + 1)
    return main_df.reindex(columns=MAIN_AED_COLUMNS + ["Liczba źródeł"])


def main_df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8", date_format="%Y-%m-%d")
    return buf.getvalue()


def main_df_to_geojson(df: pd.DataFrame) -> Dict[str, Any]:
    features = []
    for _, row in df.iterrows():
        props = {k: (None if pd.isna(v) else (v.isoformat() if hasattr(v, "isoformat") else v)) for k, v in row.items() if k not in (COL_LAT, COL_LON)}
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
    from django.conf import settings

    from mcod.resources.models import Resource

    main = get_main_aed_resource()
    qs = Resource.objects.filter(contains_aed_list=True, status="published")
    if getattr(settings, "AED_REQUIRE_VALIDATED_SOURCES", True):
        qs = qs.filter(data_tasks_last_status="SUCCESS", file_tasks_last_status="SUCCESS", link_tasks_last_status="SUCCESS")
    if main:
        qs = qs.exclude(id=main.pk)
    return qs.select_related("dataset__organization").order_by("dataset__organization__title")


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


def collect_sources() -> List[Tuple[pd.DataFrame, Dict[str, Any]]]:
    sources = []
    for resource in get_source_resources():
        try:
            df = read_source_df(resource)
        except AEDResourceReadError as exc:
            logger.error("Skipping AED source: %s", exc)
            continue
        if not validate_aed_df_columns(df):
            logger.error("Skipping AED source %s: invalid columns", resource.pk)
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


def create_main_aed_file(directory: Optional[Path] = None) -> Path:
    from django.conf import settings

    directory = Path(directory or settings.MAIN_AED_RESOURCE_CREATION_ROOT)
    directory.mkdir(parents=True, exist_ok=True)
    main_df = build_main_df(collect_sources())
    path = directory / f"{settings.MAIN_AED_FILE_NAME_PREFIX} {datetime.datetime.now():%Y%m%d}.csv"
    path.write_bytes(main_df_to_csv_bytes(main_df))
    return path


def _get_or_create_main_dataset():
    from django.apps import apps
    from django.conf import settings
    from django.db import transaction

    from mcod.aed.models import AggregatedAEDInfo

    info = AggregatedAEDInfo.objects.last()
    if info and info.main_aed_dataset:
        return info.main_aed_dataset

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
        )
        dataset.categories.set(Category.objects.filter(title__in=settings.MAIN_AED_DATASET_CATEGORIES_TITLES))
        tags = [Tag.objects.get_or_create(name=n, language="pl")[0] for n in settings.MAIN_AED_DATASET_TAGS_NAMES]
        dataset.tags.set(tags)
        dataset.save()
    return dataset


def create_main_aed_resource(file_path: Path):
    """Tworzy zasób zbiorczy (CSV) w zbiorze danych i podmienia wskaźnik AggregatedAEDInfo."""
    from django.conf import settings
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import transaction

    from mcod.aed.models import AggregatedAEDInfo
    from mcod.resources.models import Resource, ResourceFile

    old = get_main_aed_resource()
    with transaction.atomic():
        dataset = _get_or_create_main_dataset()
        resource = Resource.objects.create(
            title=old.title if old else settings.MAIN_AED_RESOURCE_DEFAULT_TITLE,
            description=old.description if old else settings.MAIN_AED_RESOURCE_DEFAULT_DESC,
            dataset=dataset,
            has_dynamic_data=True,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            contains_aed_list=True,
            status="published",
            data_date=datetime.date.today(),
        )
        upload = SimpleUploadedFile(name=file_path.name, content=file_path.read_bytes(), content_type="text/csv")
        ResourceFile.objects.create(resource=resource, is_main=True, file=upload)

        info = AggregatedAEDInfo.objects.last()
        if info:
            info.resource = resource
            info.save()
        else:
            AggregatedAEDInfo.objects.create(resource=resource)
        if old:
            old.delete()
    return resource

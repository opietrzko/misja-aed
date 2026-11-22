import datetime

import pandas as pd
import pytest

from mcod.aed.constants import AED_COLUMNS, COL_ID, COL_LAT, COL_LON, COL_PROVIDER, COL_SCOPE, MAIN_AED_COLUMNS
from mcod.aed.utils import (
    apply_aed_geo_schema,
    AEDMissingRequiredColumnError,
    build_main_df,
    check_row,
    deduplicate,
    main_df_to_geojson,
    sanitize_source_df,
    validate_aed_df_columns,
)


def make_row(**over):
    row = {
        "Lp.": 1,
        "Identyfikator AED": "A-1",
        "Szerokość geograficzna": 50.06,
        "Długość geograficzna": 19.93,
        "Miejscowość": "Kraków",
        "Ulica i numer": "ul. Floriańska 1",
        "Kod TERYT gminy": "1261011",
        "Opis lokalizacji": "hol",
        "Rodzaj obiektu": "urząd",
        "Dostępność": "całodobowo",
        "Godziny dostępności": None,
        "Sposób dostępu": "swobodny",
        "Status urządzenia": "czynny",
        "Data ostatniej weryfikacji": "2026-11-01",
        "Kontakt instytucjonalny": "bhp@example.pl",
    }
    row.update(over)
    return row


def make_df(*rows):
    return pd.DataFrame(list(rows), columns=AED_COLUMNS)


def test_validate_columns_ok_and_wrong_order():
    assert validate_aed_df_columns(make_df(make_row()))
    assert not validate_aed_df_columns(make_df(make_row())[list(reversed(AED_COLUMNS))])


@pytest.mark.parametrize(
    "override,fragment",
    [
        ({"Szerokość geograficzna": 10.0}, "poza obszarem Polski"),
        ({"Szerokość geograficzna": "abc"}, "nie są liczbami"),
        ({"Status urządzenia": "zepsuty"}, "niedozwolona wartość"),
        ({"Data ostatniej weryfikacji": "wczoraj"}, "niepoprawna data"),
        ({"Identyfikator AED": ""}, "brak wartości"),
    ],
)
def test_check_row_rejects(override, fragment):
    assert fragment in check_row(pd.Series(make_row(**override)))


def test_check_row_accepts_comma_decimal():
    assert check_row(pd.Series(make_row(**{"Szerokość geograficzna": "50,06", "Długość geograficzna": "19,93"}))) is None


def test_sanitize_drops_bad_rows_only():
    df = make_df(make_row(), make_row(**{"Identyfikator AED": "A-2", "Status urządzenia": "zepsuty"}))
    clean, rejected = sanitize_source_df(df)
    assert list(clean[COL_ID]) == ["A-1"]
    assert len(rejected) == 1 and rejected[0]["id"] == "A-2" and rejected[0]["row"] == 3


def test_sanitize_missing_required_column():
    with pytest.raises(AEDMissingRequiredColumnError):
        sanitize_source_df(make_df(make_row()).drop(columns=["Status urządzenia"]))


def test_deduplicate_merges_close_points_keeps_best():
    df = make_df(
        make_row(**{"Identyfikator AED": "old", "Status urządzenia": "do weryfikacji"}),
        make_row(**{"Identyfikator AED": "new", "Szerokość geograficzna": 50.06005}),  # ~5 m dalej
        make_row(**{"Identyfikator AED": "far", "Szerokość geograficzna": 50.07}),
    )
    clean, _ = sanitize_source_df(df)
    result = deduplicate(clean)
    assert sorted(result[COL_ID]) == ["far", "new"]
    assert result.set_index(COL_ID).loc["new", "Liczba źródeł"] == 2


def test_build_main_df_adds_provider_and_scope():
    a = make_df(make_row())
    b = make_df(make_row(**{"Identyfikator AED": "B-1", "Szerokość geograficzna": 52.2, "Długość geograficzna": 21.0}))
    main = build_main_df(
        [
            (a, {"provider": "Miasto Kraków", "scope": "AED w budynkach miasta", "resource_id": 1, "data_date": datetime.date(2026, 11, 1)}),
            (b, {"provider": "Fundacja X", "scope": "AED w Warszawie", "resource_id": 2, "data_date": None}),
        ]
    )
    assert list(main.columns[: len(MAIN_AED_COLUMNS)]) == MAIN_AED_COLUMNS
    assert set(main[COL_PROVIDER]) == {"Miasto Kraków", "Fundacja X"}
    assert set(main[COL_SCOPE]) == {"AED w budynkach miasta", "AED w Warszawie"}
    assert list(main["Lp."]) == [1, 2]


def test_geojson_has_lon_lat_order():
    a = make_df(make_row())
    main = build_main_df([(a, {"provider": "P", "scope": "S", "resource_id": 1, "data_date": None})])
    geo = main_df_to_geojson(main)
    assert geo["features"][0]["geometry"]["coordinates"] == [19.93, 50.06]
    assert COL_LAT not in geo["features"][0]["properties"] and COL_LON not in geo["features"][0]["properties"]


def test_apply_geo_schema_maps_coordinates_and_label_and_is_idempotent():
    tds = {"fields": [{"name": c, "type": "string", "format": "default"} for c in AED_COLUMNS]}
    out = apply_aed_geo_schema(tds)
    assert out["geo"]["b"]["col_name"] == "Szerokość geograficzna"
    assert out["geo"]["l"]["col_name"] == "Długość geograficzna"
    assert out["geo"]["label"]["col_name"] == "Ulica i numer"
    assert out["fields"][out["geo"]["b"]["col_index"]]["geo"] == "b"
    assert apply_aed_geo_schema(out) == out


def test_apply_geo_schema_without_columns_adds_nothing():
    tds = {"fields": [{"name": "inna", "type": "string", "format": "default"}]}
    assert "geo" not in apply_aed_geo_schema(tds)

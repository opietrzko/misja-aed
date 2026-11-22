import datetime
import json

import pandas as pd
import pytest

from mcod.aed.constants import (
    AED_COLUMNS,
    COL_DAYS_SINCE,
    COL_FRESHNESS,
    COL_ID,
    COL_LAT,
    COL_LON,
    COL_OTHER_PROVIDERS,
    COL_PROVIDER,
    COL_SCOPE,
    COL_SOURCES_COUNT,
    MAIN_AED_COLUMNS,
)
from mcod.aed.utils import (
    AEDMissingRequiredColumnError,
    apply_aed_geo_schema,
    build_main_df,
    build_report_df,
    check_row,
    compute_freshness,
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
    assert result.set_index(COL_ID).loc["new", COL_SOURCES_COUNT] == 2


def test_build_main_df_adds_provider_and_scope():
    a = make_df(make_row())
    b = make_df(make_row(**{"Identyfikator AED": "B-1", "Szerokość geograficzna": 52.2, "Długość geograficzna": 21.0}))
    main = build_main_df(
        [
            (
                a,
                {
                    "provider": "Miasto Kraków",
                    "scope": "AED w budynkach miasta",
                    "resource_id": 1,
                    "data_date": datetime.date(2026, 11, 1),
                },
            ),
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


def _with_provider(rows, provider):
    df = make_df(*rows)
    df[COL_PROVIDER] = provider
    return df


def test_dedup_lists_all_other_providers():
    a = _with_provider([make_row(**{"Identyfikator AED": "A-1"})], "Urząd")
    b = _with_provider([make_row(**{"Identyfikator AED": "B-1", "Szerokość geograficzna": 50.06003})], "Fundacja")
    c = _with_provider(
        [make_row(**{"Identyfikator AED": "C-1", "Szerokość geograficzna": 50.06004, "Status urządzenia": "do weryfikacji"})],
        "Straż",
    )
    clean, _ = sanitize_source_df(pd.concat([a, b, c], ignore_index=True))
    result = deduplicate(clean)
    assert len(result) == 1
    row = result.iloc[0]
    assert row[COL_SOURCES_COUNT] == 3
    assert "(" in row[COL_OTHER_PROVIDERS] and row[COL_OTHER_PROVIDERS].count(";") == 1  # dwóch pozostałych dysponentów
    assert {"Urząd", "Fundacja", "Straż"} == {
        row[COL_PROVIDER],
        *[p.split(" (")[0] for p in row[COL_OTHER_PROVIDERS].split("; ")],
    }


def test_dedup_does_not_merge_two_devices_of_same_provider():
    df = _with_provider(
        [make_row(**{"Identyfikator AED": "A-1"}), make_row(**{"Identyfikator AED": "A-2", "Szerokość geograficzna": 50.06004})],
        "Urząd",
    )
    clean, _ = sanitize_source_df(df)
    result = deduplicate(clean)
    assert sorted(result[COL_ID]) == ["A-1", "A-2"]
    assert list(result[COL_SOURCES_COUNT]) == [1, 1]


TODAY = datetime.date(2026, 11, 22)


@pytest.mark.parametrize(
    "verified,status,expected,days",
    [
        (datetime.date(2026, 11, 1), "czynny", "aktualny", 21),
        (datetime.date(2025, 6, 1), "czynny", "do weryfikacji", 539),  # starsze niż rok
        (datetime.date(2024, 6, 1), "czynny", "nieaktualny", 904),  # starsze niż 2 lata
        (datetime.date(2026, 11, 1), "do weryfikacji", "do weryfikacji", 21),
        (datetime.date(2026, 11, 1), "nieczynny", "nieczynny", 21),
        (datetime.date(2027, 1, 1), "czynny", "do weryfikacji", -40),  # data z przyszłości jest podejrzana
        (None, "czynny", "do weryfikacji", None),
    ],
)
def test_compute_freshness(verified, status, expected, days):
    assert compute_freshness(verified, status, TODAY) == (expected, days)


def test_build_main_df_adds_freshness_columns():
    df = make_df(
        make_row(**{"Data ostatniej weryfikacji": "2026-11-01"}),
        make_row(
            **{
                "Identyfikator AED": "B",
                "Szerokość geograficzna": 52.2,
                "Długość geograficzna": 21.0,
                "Data ostatniej weryfikacji": "2023-01-01",
            }
        ),
    )
    main = build_main_df([(df, {"provider": "P", "scope": "S", "resource_id": 1, "data_date": None})], today=TODAY)
    by_id = main.set_index(COL_ID)
    assert by_id.loc["A-1", COL_FRESHNESS] == "aktualny" and by_id.loc["A-1", COL_DAYS_SINCE] == 21
    assert by_id.loc["B", COL_FRESHNESS] == "nieaktualny"


def test_report_lists_rejected_rows_and_merged_duplicates():
    a = make_df(
        make_row(**{"Identyfikator AED": "A-1"}), make_row(**{"Identyfikator AED": "A-2", "Status urządzenia": "zepsuty"})
    )
    b = make_df(make_row(**{"Identyfikator AED": "B-1", "Szerokość geograficzna": 50.06003}))
    report = []
    main = build_main_df(
        [
            (a, {"provider": "Urząd", "scope": "S", "resource_id": 1, "data_date": None}),
            (b, {"provider": "Fundacja", "scope": "S", "resource_id": 2, "data_date": None}),
        ],
        today=TODAY,
        report=report,
    )
    assert len(main) == 1
    by_result = {r["Wynik"]: r for r in report}
    rej = by_result["odrzucono wiersz"]
    assert (rej["Dysponent"], rej["Zasób źródłowy"], rej["Wiersz w pliku"], rej["Identyfikator AED"]) == ("Urząd", 1, 3, "A-2")
    merged = by_result["połączono z innym dysponentem"]
    assert merged["Dysponent"] == "Fundacja" and merged["Wiersz w pliku"] == 2 and "A-1" in merged["Powód"]


def test_empty_report_has_single_ok_row_so_portal_accepts_the_file():
    df = build_report_df([])
    assert len(df) == 1 and df.iloc[0]["Wynik"] == "brak uwag"


def test_geojson_is_json_serializable_with_numpy_values():
    df = make_df(make_row())
    main = build_main_df([(df, {"provider": "P", "scope": "S", "resource_id": 1, "data_date": None})], today=TODAY)
    text = json.dumps(main_df_to_geojson(main), ensure_ascii=False)
    props = json.loads(text)["features"][0]["properties"]
    assert props["Dni od ostatniej weryfikacji"] == 21 and props["Aktualność"] == "aktualny"

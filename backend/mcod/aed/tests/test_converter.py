from pathlib import Path

import pandas as pd
import pytest

from mcod.aed.constants import (
    AED_COLUMNS,
    COL_ACCESS,
    COL_AVAILABILITY,
    COL_ID,
    COL_LAT,
    COL_LOCATION,
    COL_LON,
    COL_STATUS,
    COL_STREET,
    COL_VERIFIED,
)
from mcod.aed.converter import (
    convert_dataframe,
    from_pl1992,
    load_profile,
    map_columns,
    norm,
    normalize_access,
    normalize_availability,
    normalize_status,
    parse_coordinate,
    parse_date,
    parse_point,
    read_any,
)

DEMO = Path(__file__).resolve().parents[1] / "demo_data"


def test_norm_strips_diacritics_and_punctuation():
    assert norm("Szerokość geogr.") == "szerokosc geogr"
    assert norm("Łódź_ID") == "lodz id"


def test_parse_coordinate_formats():
    assert parse_coordinate("50,06143") == pytest.approx(50.06143)
    assert parse_coordinate(19.9) == 19.9
    assert parse_coordinate("50°03'41\"N") == pytest.approx(50 + 3 / 60 + 41 / 3600)
    assert parse_coordinate("19°56'12\"W") < 0
    assert parse_coordinate("abc") is None and parse_coordinate("") is None and parse_coordinate(None) is None


def test_parse_point_wkt_pair_and_swapped():
    assert parse_point("POINT (19.93 50.06)") == (50.06, 19.93)
    assert parse_point("50.06, 19.93") == (50.06, 19.93)
    assert parse_point("19.93; 50.06") == (50.06, 19.93)  # zamienione miejscami
    assert parse_point("10, 10") is None


def test_pl1992_conversion_and_axis_order_is_explicit():
    lat, lon = from_pl1992(566859.11, 244266.77)  # (wschód, północ)
    assert lat == pytest.approx(50.0619, abs=1e-3) and lon == pytest.approx(19.9344, abs=1e-3)
    # zamienione osie dają inny punkt (też w Polsce), dlatego kolejność nie jest zgadywana
    swapped = from_pl1992(244266.77, 566859.11)
    assert swapped is not None and swapped != (lat, lon)


def test_pl1992_north_first_option_flips_axes():
    df = pd.DataFrame(
        {
            "Y": ["244266,77"],
            "X": ["566859,11"],
            "Nr": ["1"],
            "Godziny": ["całą dobę"],
            "Stan": ["sprawny"],
            "Dostęp": ["tak"],
            "Data przeglądu": ["14.11.2026"],
        }
    )
    out, _, _ = convert_dataframe(df, pl1992_north_first=True)
    assert out.iloc[0][COL_LAT] == pytest.approx(50.0619, abs=1e-3)


def test_parse_date_iso_and_polish():
    assert str(parse_date("2026-11-03")) == "2026-11-03"
    assert str(parse_date("03.11.2026")) == "2026-11-03"
    assert parse_date("bez daty") is None


@pytest.mark.parametrize(
    "value,hours,expected",
    [
        ("całą dobę", None, "całodobowo"),
        (None, "24/7", "całodobowo"),
        (None, "Mo-Fr 8-16", "w godzinach"),
        ("ograniczona", None, "ograniczona"),
        ("tak", None, None),
    ],
)
def test_normalize_availability(value, hours, expected):
    assert normalize_availability(value, hours) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("yes", "swobodny"),
        ("customers", "za zgodą"),
        ("private", "zamknięte na klucz"),
        ("nie", "zamknięte na klucz"),
        ("nowy", None),
        (None, None),
    ],
)
def test_normalize_access(value, expected):
    assert normalize_access(value) == expected


@pytest.mark.parametrize(
    "value,expected", [("sprawny", "czynny"), ("uszkodzony", "nieczynny"), ("do sprawdzenia", "do weryfikacji"), ("???", None)]
)
def test_normalize_status(value, expected):
    assert normalize_status(value) == expected


def test_map_columns_messy_source():
    df = read_any(str(DEMO / "przyklad-inne-kolumny.csv"))
    m = map_columns(df)
    assert m.columns[COL_ID].sources == ["Nr"]
    assert m.columns[COL_STREET].sources == ["Adres"]
    assert m.columns[COL_LOCATION].sources == ["Lokalizacja w budynku"]
    assert m.columns[COL_STATUS].sources == ["Stan"]
    assert m.columns[COL_VERIFIED].sources == ["Data przeglądu"]
    assert m.pl1992 == ("Y", "X")  # współrzędne w PL-1992 wykryte po zawartości


def test_convert_messy_source_end_to_end():
    df = read_any(str(DEMO / "przyklad-inne-kolumny.csv"))
    out, report, _ = convert_dataframe(df)
    assert list(out.columns) == AED_COLUMNS
    assert len(out) == 3  # A-20 odrzucony: brak godzin/dostępności i brak daty przeglądu, a wartości domyślnych nie ma
    rejected = [r for r in report if r["wynik"] == "odrzucono"]
    assert [r["id"] for r in rejected] == ["A-20"]
    assert any("przyjęto: pierwsza kolumna = wschód" in r["szczegoly"] for r in report)
    first = out.iloc[0]
    assert first[COL_LAT] == pytest.approx(50.0619, abs=1e-3) and first[COL_LON] == pytest.approx(19.9344, abs=1e-3)
    assert first[COL_STATUS] == "czynny" and first[COL_AVAILABILITY] == "całodobowo" and first[COL_ACCESS] == "swobodny"
    assert out.iloc[1][COL_STATUS] == "nieczynny"
    assert out.iloc[0][COL_VERIFIED] == "2026-11-14"


def test_explicit_defaults_rescue_missing_values_but_only_when_given():
    df = read_any(str(DEMO / "przyklad-inne-kolumny.csv"))
    only_date, _, _ = convert_dataframe(df, defaults={COL_VERIFIED: "2026-11-20"})
    assert len(only_date) == 3  # sama data nie wystarczy, brakuje jeszcze dostępności
    both, _, _ = convert_dataframe(df, defaults={COL_VERIFIED: "2026-11-20", COL_AVAILABILITY: "w godzinach"})
    assert len(both) == 4


def test_osm_profile_overpass_json():
    df = read_any(str(DEMO / "przyklad-osm-overpass-SYNTETYCZNE.json"))
    profile = load_profile("osm")
    out, report, mapping = convert_dataframe(df, profile, defaults={COL_VERIFIED: "2026-11-20"})
    by_id = {r["id"]: r for r in report}
    assert by_id["osm-node-9000003"]["wynik"] == "odrzucono"  # brak godzin i dostępności: nic nie zgadujemy
    assert by_id["osm-node-9000004"]["wynik"] == "odrzucono"  # współrzędne poza Polską
    assert len(out) == 3
    node1 = out[out[COL_ID] == "osm-node-9000001"].iloc[0]
    assert node1[COL_AVAILABILITY] == "całodobowo" and node1[COL_ACCESS] == "swobodny" and node1[COL_STATUS] == "do weryfikacji"
    assert node1[COL_VERIFIED] == "2026-10-12"  # check_date z OSM ma pierwszeństwo przed datą domyślną
    way = out[out[COL_ID] == "osm-way-9000005"].iloc[0]
    assert way[COL_LAT] == pytest.approx(51.108)  # środek obiektu (center)


def test_output_is_accepted_by_aggregation_validation():
    from mcod.aed.utils import build_main_df

    df = read_any(str(DEMO / "przyklad-inne-kolumny.csv"))
    out, _, _ = convert_dataframe(df)
    main = build_main_df([(out, {"provider": "P", "scope": "S", "resource_id": 1, "data_date": None})])
    assert len(main) == len(out)


def test_hours_column_is_not_mistaken_for_access_column():
    """Prawdziwy układ pliku z Łodzi: 'Godz. dostępu' to godziny, a nie 'Sposób dostępu'."""
    df = pd.DataFrame(columns=["", "Podmiot", "Obiekt", "Adres", "Lokalizacja w obiekcie ", "Godz. dostępu"])
    m = map_columns(df)
    assert m.columns["Godziny dostępności"].sources == ["Godz. dostępu"]
    assert "Sposób dostępu" not in m.columns
    assert m.columns["Rodzaj obiektu"].sources == ["Obiekt"]
    assert m.columns["Ulica i numer"].sources == ["Adres"]
    assert m.columns["Opis lokalizacji"].sources == ["Lokalizacja w obiekcie "]


@pytest.mark.parametrize("value", ["caołobowo", "całodobowe", "Całodobowo", "całodobowy"])
def test_availability_tolerates_typos_in_availability_and_in_hours_column(value):
    assert normalize_availability(value) == "całodobowo"
    assert normalize_availability(None, value) == "całodobowo"  # w prawdziwym pliku literówki są w kolumnie godzin


def test_availability_typo_tolerance_does_not_touch_real_hours():
    assert normalize_availability(None, "godz: 8.00-18.00 w dni robocze") == "w godzinach"
    assert normalize_availability(None, "pn-pt 7-17") == "w godzinach"


def test_address_only_rows_are_rejected_with_actionable_reason():
    df = pd.DataFrame({"Obiekt": ["szkoła"], "Adres": ["ul. Paradna 36, 93-345 Łódź"], "Godz. dostępu": ["caołobowo"]})
    out, report, _ = convert_dataframe(
        df, defaults={COL_VERIFIED: "2026-11-20", COL_ACCESS: "za zgodą", COL_STATUS: "do weryfikacji"}
    )
    assert len(out) == 0
    assert report[0]["wynik"] == "odrzucono"
    assert "brak współrzędnych (jest adres)" in report[0]["szczegoly"] and "geokoduje" in report[0]["szczegoly"]


def test_row_without_address_and_coordinates_keeps_generic_reason():
    df = pd.DataFrame({"Obiekt": ["szkoła"], "Godziny": ["całodobowo"]})
    out, report, _ = convert_dataframe(df, defaults={COL_VERIFIED: "2026-11-20", COL_ACCESS: "swobodny", COL_STATUS: "czynny"})
    assert "(jest adres)" not in report[0]["szczegoly"]


def test_city_is_filled_from_address_when_source_has_no_city_column():
    df = pd.DataFrame(
        {
            "Adres": ["ul. Paradna 36, 93-345 Łódź"],
            "Szerokość": ["51.7592"],
            "Długość": ["19.4560"],
            "Godziny": ["całodobowo"],
            "Dostęp": ["tak"],
            "Stan": ["sprawny"],
            "Data weryfikacji": ["2026-11-01"],
        }
    )
    out, report, _ = convert_dataframe(df)
    assert len(out) == 1, report
    assert out.iloc[0]["Miejscowość"] == "Łódź"


def test_generated_ids_follow_file_position_even_for_rejected_rows():
    df = pd.DataFrame(
        {
            "Adres": ["ul. A 1, 00-001 Miastowo", "ul. B 2, 00-002 Miastowo", "ul. C 3, 00-003 Miastowo"],
            "Godziny": ["całodobowo"] * 3,
        }
    )
    _, report, _ = convert_dataframe(
        df, defaults={COL_VERIFIED: "2026-11-20", COL_ACCESS: "za zgodą", COL_STATUS: "do weryfikacji"}
    )
    assert [r["id"] for r in report] == ["AED-0001", "AED-0002", "AED-0003"]  # różne identyfikatory w raporcie


def test_ewidence_number_header_is_recognised_as_identifier():
    m = map_columns(pd.DataFrame(columns=["Nr ewid.", "Miasto", "Ulica"]))
    assert m.columns[COL_ID].sources == ["Nr ewid."]

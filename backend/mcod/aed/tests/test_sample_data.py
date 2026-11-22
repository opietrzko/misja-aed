"""Pilnuje, że przykładowe dane (folder przykladowe-dane/) i opisy w ich README pozostają prawdziwe.

Folder leży poza backend/, więc w kontenerze (który montuje tylko backend/mcod) testy są pomijane.
"""

from pathlib import Path

import pandas as pd
import pytest

from mcod.aed.constants import (
    COL_ACCESS,
    COL_AVAILABILITY,
    COL_FRESHNESS,
    COL_ID,
    COL_STATUS,
    COL_VERIFIED,
)
from mcod.aed.converter import convert_dataframe, load_profile, read_any
from mcod.aed.utils import build_main_df, validate_aed_df_columns

ROOT = Path(__file__).resolve().parents[4]
SAMPLES = ROOT / "przykladowe-dane"
DEMO_DATA = ROOT / "backend" / "mcod" / "aed" / "demo_data"
if not SAMPLES.exists():
    pytest.skip("brak folderu przykladowe-dane (np. w kontenerze)", allow_module_level=True)

PROVIDERS = ["urzad-miasta-demo-krakow", "fundacja-demo-ratownik", "wcr-demo-gdansk"]
ORGANIZATIONS = {  # dysponent w portalu to tytuł instytucji, którą tworzy aed_seed_demo
    "urzad-miasta-demo-krakow": "Urząd Miasta Demo-Kraków",
    "fundacja-demo-ratownik": "Fundacja Demo-Ratownik",
    "wcr-demo-gdansk": "Wojewódzkie Centrum Ratownictwa Demo-Gdańsk",
}


def convert(path, profile=None, defaults=None):
    out, report, mapping = convert_dataframe(read_any(str(path)), load_profile(profile) if profile else None, defaults or {})
    return out, {r["id"]: r for r in report}, mapping


def merge(frames):
    report = []
    sources = [
        (df, {"provider": name, "scope": "demo", "resource_id": i, "data_date": None}) for i, (name, df) in enumerate(frames, 1)
    ]
    return build_main_df(sources, report=report), report


# --- 01: wykazy dostawców ---


def test_providers_have_standard_columns_and_xlsx_matches_csv():
    for name in PROVIDERS:
        csv = pd.read_csv(SAMPLES / "01-wykazy-dostawcow" / f"{name}.csv")
        xlsx = pd.read_excel(SAMPLES / "01-wykazy-dostawcow" / f"{name}.xlsx")
        assert validate_aed_df_columns(csv) and validate_aed_df_columns(xlsx)
        assert len(csv) == len(xlsx)


def test_providers_merge_as_documented():
    frames = [(ORGANIZATIONS[n], pd.read_csv(SAMPLES / "01-wykazy-dostawcow" / f"{n}.csv")) for n in PROVIDERS]
    assert sum(len(df) for _, df in frames) == 14
    main, report = merge(frames)
    assert len(main) == 11
    by_id = {r["Identyfikator AED"]: r for r in report}
    assert len(report) == 3
    assert by_id["FDR-0005"]["Wynik"] == by_id["FDR-0006"]["Wynik"] == "odrzucono wiersz"
    assert (by_id["FDR-0005"]["Wiersz w pliku"], by_id["FDR-0006"]["Wiersz w pliku"]) == (6, 7)
    merged = by_id["DEMO-UM-001"]
    assert merged["Wynik"] == "połączono z innym dysponentem" and merged["Wiersz w pliku"] == 2
    assert "FDR-0001" in merged["Powód"] and "pewność 99%" in merged["Powód"]
    fdr1 = main[main[COL_ID] == "FDR-0001"].iloc[0]
    assert fdr1["Liczba źródeł"] == 2 and "Urząd Miasta Demo-Kraków (DEMO-UM-001)" in fdr1["Pozostali dysponenci"]
    assert main["Nazwa dysponenta zasobu"].value_counts().to_dict() == {
        "Fundacja Demo-Ratownik": 4,
        "Urząd Miasta Demo-Kraków": 4,
        "Wojewódzkie Centrum Ratownictwa Demo-Gdańsk": 3,
    }


def test_demo_data_copies_are_in_sync():
    for name in PROVIDERS:
        assert (SAMPLES / "01-wykazy-dostawcow" / f"{name}.csv").read_bytes() == (DEMO_DATA / f"{name}.csv").read_bytes()
    for name in ("przyklad-inne-kolumny.csv", "przyklad-osm-overpass-SYNTETYCZNE.json"):
        assert (SAMPLES / "02-konwerter" / name).read_bytes() == (DEMO_DATA / name).read_bytes()


# --- 02: konwerter ---


def test_other_columns_sample():
    path = SAMPLES / "02-konwerter" / "przyklad-inne-kolumny.csv"
    out, rows, _ = convert(path)
    assert len(out) == 3 and rows["A-20"]["wynik"] == "odrzucono"
    assert all("PL-1992" in rows[i]["szczegoly"] for i in ("A-17", "A-18", "A-19"))
    out_all, _, _ = convert(path, defaults={COL_VERIFIED: "2026-11-20", COL_AVAILABILITY: "w godzinach"})
    assert len(out_all) == 4


def test_osm_sample():
    out, rows, _ = convert(
        SAMPLES / "02-konwerter" / "przyklad-osm-overpass-SYNTETYCZNE.json", "osm", {COL_VERIFIED: "2026-11-20"}
    )
    assert len(out) == 3
    assert rows["osm-node-9000003"]["wynik"] == rows["osm-node-9000004"]["wynik"] == "odrzucono"
    assert set(out[COL_STATUS]) == {"do weryfikacji"}
    assert "za zgodą" in set(out[COL_ACCESS])  # access=customers


def test_polish_headers_sample():
    out, rows, mapping = convert(SAMPLES / "02-konwerter" / "przyklad-polskie-naglowki.xlsx")
    assert (
        len(out) == 5 and rows["PL-005"]["wynik"] == "odrzucono" and "Data ostatniej weryfikacji" in rows["PL-005"]["szczegoly"]
    )
    by_id = out.set_index(COL_ID)
    assert by_id.loc["PL-003", COL_AVAILABILITY] == "całodobowo"  # literówka "caołobowo"
    assert by_id.loc["PL-004", COL_STATUS] == "nieczynny"
    assert "zamieniono szerokość z długością" in rows["PL-004"]["szczegoly"]
    assert by_id.loc["PL-006", COL_STATUS] == "do weryfikacji"
    assert mapping.columns["Identyfikator AED"].sources == ["Nr ewid."]


def test_single_coordinate_column_sample():
    out, rows, mapping = convert(SAMPLES / "02-konwerter" / "przyklad-wspolrzedne-w-jednej-kolumnie.csv")
    assert len(out) == 3 and mapping.combined_point == "Punkt"
    by_id = out.set_index(COL_ID)
    assert list(by_id["Miejscowość"]) == ["Kraków", "Warszawa", "Gdańsk"]
    assert (by_id.loc["GD-01", "Szerokość geograficzna"], by_id.loc["GD-01", "Długość geograficzna"]) == (
        54.35205,
        18.64637,
    )  # odwrócona kolejność
    assert all("współrzędne z jednej kolumny" in r["szczegoly"] for r in rows.values())


# --- 03: pliki odrzucane ---


def test_rejected_files_behave_as_documented():
    folder = SAMPLES / "03-pliki-odrzucane"
    assert not validate_aed_df_columns(pd.read_csv(folder / "zle-kolumny.csv"))
    assert (folder / "zly-format.txt").exists()

    defaults = {COL_VERIFIED: "2026-11-20", COL_ACCESS: "za zgodą", COL_STATUS: "do weryfikacji"}
    out, rows, _ = convert(folder / "tylko-adresy-bez-wspolrzednych.csv", defaults=defaults)
    assert len(out) == 0 and sorted(rows) == ["AED-0001", "AED-0002", "AED-0003", "AED-0004"]
    assert all("brak współrzędnych (jest adres)" in r["szczegoly"] for r in rows.values())

    outside = pd.read_csv(folder / "wspolrzedne-poza-polska.csv")
    assert validate_aed_df_columns(outside)
    main, report = merge([("X", outside)])
    assert len(main) == 1 and sorted((r["Wiersz w pliku"], r["Identyfikator AED"]) for r in report) == [
        (3, "OUT-002"),
        (4, "OUT-003"),
    ]
    assert set(main[COL_FRESHNESS]) <= {"aktualny", "do weryfikacji", "nieaktualny", "nieczynny"}


# --- 05: import XML ---


def test_xml_sample_is_valid_for_1_14_and_rejected_by_1_13():
    xmlschema = pytest.importorskip("xmlschema")
    xml = SAMPLES / "05-import-xml" / "przyklad-harvester-1.14.xml"
    data = ROOT / "backend" / "data" / "harvester"
    assert xmlschema.XMLSchema(str(data / "xml_import_otwarte_dane_1_14.xsd")).is_valid(str(xml))
    as_13 = xml.read_text(encoding="utf-8").replace("harvester:1.14", "harvester:1.13")
    assert not xmlschema.XMLSchema(str(data / "xml_import_otwarte_dane_1_13.xsd")).is_valid(as_13)

"""Generuje SYNTETYCZNE pliki przykładowe do importu i testów (fikcyjni dysponenci, zmyślone dane).

Powstaje folder ``przykladowe-dane/`` (wykazy dostawców, pliki dla konwertera, pliki odrzucane) oraz kopie wykazów
dostawców w ``backend/mcod/aed/demo_data/``, z których korzysta komenda ``aed_seed_demo``.
Dwa pliki dla konwertera (inne kolumny z PL-1992 i format Overpass) są statyczne i leżą w ``demo_data``; generator je kopiuje.

Uruchomienie (z katalogu backend):  PYTHONPATH=. python ../aed-demo/generate_demo.py
"""

import shutil
from pathlib import Path

import pandas as pd

from mcod.aed.constants import AED_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "przykladowe-dane"
DEMO_DATA = ROOT / "backend" / "mcod" / "aed" / "demo_data"


def row(i, id_, lat, lon, city, street, teryt, loc, obj, avail, hours, access, status, verified, contact="demo@example.pl"):
    return [i, id_, lat, lon, city, street, teryt, loc, obj, avail, hours, access, status, verified, contact]


MIASTO = [  # "Urząd Miasta Demo-Kraków" - AED w budynkach miejskich
    row(1, "DEMO-UM-001", 50.06143, 19.93658, "Kraków", "ul. Floriańska 1", "1261011", "hol główny, przy recepcji", "urząd", "w godzinach", "pn-pt 7:30-16:00", "swobodny", "czynny", "2026-11-03"),
    row(2, "DEMO-UM-002", 50.05780, 19.93720, "Kraków", "pl. Wszystkich Świętych 3", "1261011", "parter, portiernia", "urząd", "całodobowo", None, "swobodny", "czynny", "2026-10-20"),
    row(3, "DEMO-UM-003", 50.06465, 19.94498, "Kraków", "Dworzec Główny, hala", "1261011", "przy kasach", "dworzec", "całodobowo", None, "swobodny", "czynny", "2026-11-10"),
    row(4, "DEMO-UM-004", 50.04960, 19.94480, "Kraków", "ul. Dietla 50", "1261011", "wejście od podwórza", "szkoła", "w godzinach", "pn-pt 7:00-18:00", "za zgodą", "do weryfikacji", "2025-12-01"),
    row(5, "DEMO-UM-005", 50.06700, 19.91200, "Kraków", "ul. Błędna 9", "1261011", "hol", "urząd", "całodobowo", None, "swobodny", "czynny", "2026-11-01"),
]

FUNDACJA = [  # "Fundacja Demo-Ratownik" - AED w przestrzeni publicznej, część w Krakowie (duplikaty z miastem)
    row(1, "FDR-0001", 50.06146, 19.93655, "Kraków", "ul. Floriańska 1", "1261011", "wejście główne", "urząd", "w godzinach", "pn-pt 7:30-16:00", "swobodny", "czynny", "2026-11-15"),
    row(2, "FDR-0002", 50.06000, 19.93800, "Kraków", "Rynek Główny 20", "1261011", "kiosk ratunkowy", "przestrzeń publiczna", "całodobowo", None, "swobodny", "czynny", "2026-11-12"),
    row(3, "FDR-0003", 52.22977, 21.01178, "Warszawa", "Krakowskie Przedmieście 5", "1465011", "budka przy bramie", "przestrzeń publiczna", "całodobowo", None, "swobodny", "czynny", "2026-11-05"),
    row(4, "FDR-0004", 52.24000, 21.01000, "Warszawa", "ul. Przykładowa 7", "1465011", "klatka A", "budynek mieszkalny", "ograniczona", None, "zamknięte na klucz", "czynny", "2026-09-01"),
    row(5, "FDR-0005", 10.0, 21.01000, "Warszawa", "ul. Błędna 1", "1465011", "szerokość poza Polską", "inne", "całodobowo", None, "swobodny", "czynny", "2026-11-05"),
    row(6, "FDR-0006", 52.23100, 21.00500, "Warszawa", "ul. Zła 2", "1465011", "zły status", "inne", "całodobowo", None, "swobodny", "zepsuty", "2026-11-05"),
]

WCR = [  # "Wojewódzkie Centrum Ratownictwa Demo" - AED w Gdańsku
    row(1, "WCR-GD-01", 54.35205, 18.64637, "Gdańsk", "Długi Targ 1", "2261011", "przy fontannie Neptuna", "przestrzeń publiczna", "całodobowo", None, "swobodny", "czynny", "2026-11-18"),
    row(2, "WCR-GD-02", 54.35600, 18.64300, "Gdańsk", "Dworzec Główny", "2261011", "hala główna", "dworzec", "całodobowo", None, "swobodny", "czynny", "2026-11-08"),
    row(3, "WCR-GD-03", 54.37200, 18.61300, "Gdańsk", "ul. Grunwaldzka 100", "2261011", "centrum handlowe, informacja", "galeria handlowa", "w godzinach", "codziennie 9:00-21:00", "swobodny", "czynny", "2026-11-02"),
]

FILES = {
    "urzad-miasta-demo-krakow": MIASTO,
    "fundacja-demo-ratownik": FUNDACJA,
    "wcr-demo-gdansk": WCR,
}


# --- pliki dla konwertera (inny układ niż wzorzec) ---

POLSKIE_NAGLOWKI_COLUMNS = [
    "Nr ewid.",
    "Miasto",
    "Ulica",
    "Opis miejsca",
    "Typ obiektu",
    "Szer. geogr.",
    "Dł. geogr.",
    "Godz. dostępności",
    "Stan urządzenia",
    "Dostęp",
    "Data kontroli",
]
POLSKIE_NAGLOWKI = [  # wszystko tekstem, jak w Excelu: przecinek dziesiętny, literówki, różne zapisy godzin i dat
    ["PL-001", "Poznań", "pl. Wolności 1", "przy windzie", "urząd", "52,40800", "16,93400", "pn-pt 7-16", "sprawny", "tak", "05.11.2026"],
    ["PL-002", "Poznań", "ul. Półwiejska 42", "galeria, informacja", "galeria handlowa", "52,40000", "16,92900", "codziennie 9:00-21:00", "sprawny", "tak", "12.11.2026"],
    ["PL-003", "Wrocław", "Rynek 1", "hol ratusza", "urząd", "51,10990", "17,03190", "caołobowo", "sprawny", "tak", "2026-10-02"],
    ["PL-004", "Wrocław", "ul. Świdnicka 3", "za portiernią", "budynek biurowy", "17,03000", "51,10700", "godz: 8.00-18.00 w dni robocze", "uszkodzony", "za zgodą", "18.09.2026"],
    ["PL-005", "Gdynia", "ul. Świętojańska 10", "hol", "urząd", "54,51890", "18,53880", "całodobowe", "sprawny", "tak", ""],
    ["PL-006", "Gdynia", "ul. Morska 1", "kiosk", "przestrzeń publiczna", "54,52000", "18,52000", "24/7", "do sprawdzenia", "tak", "01.11.2026"],
]

JEDNA_KOLUMNA_COLUMNS = ["ID", "Adres", "Punkt", "Godziny", "Stan", "Dostęp", "Data weryfikacji"]
JEDNA_KOLUMNA = [  # współrzędne w jednej kolumnie: "szer, dł", WKT i odwrócona kolejność "dł; szer"
    ["KR-01", "ul. Floriańska 1, 31-019 Kraków", "50.06143, 19.93658", "całodobowo", "czynny", "swobodny", "2026-11-10"],
    ["WA-01", "Krakowskie Przedmieście 5, 00-068 Warszawa", "POINT (21.01178 52.22977)", "pn-pt 8-18", "czynny", "swobodny", "2026-11-05"],
    ["GD-01", "Długi Targ 1, 80-828 Gdańsk", "18.64637; 54.35205", "codziennie 9-21", "czynny", "za zgodą", "2026-11-18"],
]

# --- pliki odrzucane ---

TYLKO_ADRESY_COLUMNS = ["Lp.", "Podmiot", "Obiekt", "Adres", "Lokalizacja w obiekcie", "Godz. dostępu"]
TYLKO_ADRESY = [  # układ jak w prawdziwych wykazach urzędów: sam adres, bez współrzędnych (miejscowość fikcyjna)
    ["1", "Szkoła Podstawowa nr 99 (dane demo)", "szkoła", "ul. Przykładowa 12, 00-001 Miastowo", "hol główny", "całodobowo"],
    ["2", "Dom Kultury (dane demo)", "dom kultury", "ul. Wymyślona 3, 00-002 Miastowo", "przy wejściu", "pn-pt 8-16"],
    ["3", "Urząd Gminy (dane demo)", "urząd", "pl. Wzorcowy 1, 00-003 Miastowo", "parter, portiernia", "caołobowo"],
    ["4", "Przychodnia (dane demo)", "przychodnia", "ul. Testowa 7/9 Miastowo", "I piętro", "godz: 8.00-18.00 w dni robocze"],
]
POZA_POLSKA = [  # poprawny układ kolumn, ale dwa punkty leżą poza Polską
    row(1, "OUT-001", 50.06143, 19.93658, "Kraków", "ul. Floriańska 1", "1261011", "hol", "urząd", "całodobowo", None, "swobodny", "czynny", "2026-11-03"),
    row(2, "OUT-002", 10.00000, 19.93658, "Nigdzie", "ul. Zła 1", None, "szerokość poza Polską", "inne", "całodobowo", None, "swobodny", "czynny", "2026-11-03"),
    row(3, "OUT-003", 50.06143, 40.00000, "Nigdzie", "ul. Zła 2", None, "długość poza Polską", "inne", "całodobowo", None, "swobodny", "czynny", "2026-11-03"),
]
ZLE_KOLUMNY = [list(reversed(r)) for r in [row(1, "ZK-001", 50.06143, 19.93658, "Kraków", "ul. Floriańska 1", "1261011", "hol", "urząd", "całodobowo", None, "swobodny", "czynny", "2026-11-03")]]


def write(df: pd.DataFrame, path: Path, excel: bool = False, sep: str = ",") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if excel:
        df.to_excel(path, index=False, sheet_name="Arkusz 1")
    else:
        df.to_csv(path, index=False, sep=sep)
    print("zapisano", path.relative_to(ROOT))


def main() -> None:
    providers_dir = OUT / "01-wykazy-dostawcow"
    for name, rows in FILES.items():
        df = pd.DataFrame(rows, columns=AED_COLUMNS)
        write(df, providers_dir / f"{name}.csv")
        write(df, providers_dir / f"{name}.xlsx", excel=True)
        write(df, DEMO_DATA / f"{name}.csv")  # kopia dla aed_seed_demo

    converter_dir = OUT / "02-konwerter"
    for static in ("przyklad-inne-kolumny.csv", "przyklad-osm-overpass-SYNTETYCZNE.json"):
        converter_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEMO_DATA / static, converter_dir / static)
        print("skopiowano", (converter_dir / static).relative_to(ROOT))
    write(pd.DataFrame(POLSKIE_NAGLOWKI, columns=POLSKIE_NAGLOWKI_COLUMNS), converter_dir / "przyklad-polskie-naglowki.xlsx", excel=True)
    write(pd.DataFrame(JEDNA_KOLUMNA, columns=JEDNA_KOLUMNA_COLUMNS), converter_dir / "przyklad-wspolrzedne-w-jednej-kolumnie.csv", sep=";")

    rejected_dir = OUT / "03-pliki-odrzucane"
    write(pd.DataFrame(ZLE_KOLUMNY, columns=list(reversed(AED_COLUMNS))), rejected_dir / "zle-kolumny.csv")
    write(pd.DataFrame(TYLKO_ADRESY, columns=TYLKO_ADRESY_COLUMNS), rejected_dir / "tylko-adresy-bez-wspolrzednych.csv")
    write(pd.DataFrame(POZA_POLSKA, columns=AED_COLUMNS), rejected_dir / "wspolrzedne-poza-polska.csv")
    (rejected_dir / "zly-format.txt").write_text(
        "To nie jest wykaz AED w formacie csv, xls ani xlsx.\nFormularz zasobu odrzuci ten plik jako wykaz AED.\n", encoding="utf-8"
    )
    print("zapisano", (rejected_dir / "zly-format.txt").relative_to(ROOT))


if __name__ == "__main__":
    main()

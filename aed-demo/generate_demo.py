"""Generuje SYNTETYCZNE wykazy demonstracyjne AED trzech fikcyjnych dysponentów.

Dane są zmyślone (współrzędne w pobliżu centrów miast, identyfikatory DEMO-*) i służą
wyłącznie do pokazania działania portalu: walidacji kolumn, odrzucania błędnych
wierszy, deduplikacji między dysponentami i scalania w wykaz zbiorczy.

Uruchomienie (z katalogu backend):  PYTHONPATH=. python ../aed-demo/generate_demo.py ../aed-demo/out
"""

import sys
from pathlib import Path

import pandas as pd

from mcod.aed.constants import AED_COLUMNS


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


def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in FILES.items():
        df = pd.DataFrame(rows, columns=AED_COLUMNS)
        df.to_csv(out / f"{name}.csv", index=False)
        df.to_excel(out / f"{name}.xlsx", index=False, sheet_name="Arkusz 1")
        print("zapisano", name, len(df), "wierszy")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "aed-demo/out"))

"""Generator wzorcowego pliku xlsx (wymóg konkursowy: wzorcowy zakres danych)."""

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from mcod.aed.constants import (
    ACCESS_VALUES,
    AED_COLUMNS,
    AVAILABILITY_VALUES,
    COL_ACCESS,
    COL_AVAILABILITY,
    COL_STATUS,
    MAIN_AED_COLUMNS,
    STATUS_VALUES,
)

DESCRIPTIONS = {
    "Lp.": ("Liczba porządkowa wiersza.", "tak", "1"),
    "Identyfikator AED": ("Unikalny identyfikator urządzenia nadany przez dysponenta.", "tak", "KRK-0001"),
    "Szerokość geograficzna": (
        "WGS84, stopnie dziesiętne, kropka jako separator (zakres dla Polski 48.9–55.0).",
        "tak",
        "50.06143",
    ),
    "Długość geograficzna": (
        "WGS84, stopnie dziesiętne, kropka jako separator (zakres dla Polski 14.0–24.2).",
        "tak",
        "19.93658",
    ),
    "Miejscowość": ("Nazwa miejscowości.", "zalecane", "Kraków"),
    "Ulica i numer": ("Adres budynku lub miejsca.", "zalecane", "ul. Floriańska 1"),
    "Kod TERYT gminy": ("7-cyfrowy kod TERYT gminy (powiązanie z regionami w portalu).", "zalecane", "1261011"),
    "Opis lokalizacji": (
        "Gdzie dokładnie jest urządzenie (piętro, wejście, portiernia).",
        "zalecane",
        "hol główny, przy recepcji",
    ),
    "Rodzaj obiektu": ("Typ miejsca: urząd, szkoła, dworzec, galeria, przestrzeń publiczna…", "zalecane", "urząd"),
    "Dostępność": ("Jedna z wartości: " + ", ".join(AVAILABILITY_VALUES) + ".", "tak", "w godzinach"),
    "Godziny dostępności": ("Np. „pn–pt 7:30–16:00”; dla „całodobowo” puste.", "jeśli w godzinach", "pn–pt 7:30–16:00"),
    "Sposób dostępu": ("Jedna z wartości: " + ", ".join(ACCESS_VALUES) + ".", "tak", "swobodny"),
    "Status urządzenia": ("Jedna z wartości: " + ", ".join(STATUS_VALUES) + ".", "tak", "czynny"),
    "Data ostatniej weryfikacji": (
        "Kiedy dysponent ostatnio potwierdził urządzenie i jego stan (RRRR-MM-DD).",
        "tak",
        "2026-11-01",
    ),
    "Kontakt instytucjonalny": (
        "Adres e-mail lub telefon instytucji (bez danych osób fizycznych).",
        "zalecane",
        "bhp@urzad.example.pl",
    ),
}


AGGREGATE_NOTES = {
    "Nazwa dysponenta zasobu": "wyliczana: instytucja, która opublikowała wykaz (ponosi odpowiedzialność za dane)",
    "Zakres referencyjny źródła": "wyliczana: tytuł zasobu źródłowego, czyli zakres, który dysponent deklaruje",
    "Identyfikator zasobu źródłowego": "wyliczana: id zasobu w portalu, z którego pochodzi rekord",
    "Data aktualizacji zasobu źródłowego": "wyliczana: data danych zasobu źródłowego",
    "Liczba źródeł": "wyliczana: ile wykazów zgłosiło to samo urządzenie (punkty różnych dysponentów bliżej niż 25 m)",
    "Pozostali dysponenci": "wyliczana: pozostali dysponenci tego urządzenia w formie „Dysponent (identyfikator); …”",
    "Aktualność": (
        "wyliczana: nieczynny / nieaktualny (weryfikacja starsza niż 2 lata) / do weryfikacji "
        "(starsza niż rok, status „do weryfikacji” lub data z przyszłości) / aktualny"
    ),
    "Dni od ostatniej weryfikacji": "wyliczana: liczba dni od daty ostatniej weryfikacji do dnia scalenia",
}


def _build_workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Wykaz AED (wzór)"
    head = PatternFill("solid", fgColor="C8102E")
    for i, col in enumerate(AED_COLUMNS, start=1):
        c = ws.cell(row=1, column=i, value=col)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = head
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.cell(row=2, column=i, value=DESCRIPTIONS[col][2])
        ws.column_dimensions[c.column_letter].width = 24
    for col, values in ((COL_AVAILABILITY, AVAILABILITY_VALUES), (COL_ACCESS, ACCESS_VALUES), (COL_STATUS, STATUS_VALUES)):
        idx = AED_COLUMNS.index(col) + 1
        letter = ws.cell(row=1, column=idx).column_letter
        dv = DataValidation(type="list", formula1='"' + ",".join(values) + '"', allow_blank=False)
        ws.add_data_validation(dv)
        dv.add(f"{letter}2:{letter}5000")
    ws.freeze_panes = "A2"

    info = wb.create_sheet("Opis kolumn")
    info.append(["Kolumna", "Opis", "Wymagana", "Przykład"])
    for col in AED_COLUMNS:
        info.append([col, *DESCRIPTIONS[col][:2], DESCRIPTIONS[col][2]])
    info.column_dimensions["A"].width = 30
    info.column_dimensions["B"].width = 90
    for c in info[1]:
        c.font = Font(bold=True)

    agg = wb.create_sheet("Wykaz zbiorczy (kolumny)")
    agg.append(["Kolumna zbiorczego wykazu", "Skąd się bierze"])
    for col in MAIN_AED_COLUMNS:
        agg.append([col, AGGREGATE_NOTES.get(col, "z wykazu dostawcy (jak w arkuszu wzorca)")])
    agg.column_dimensions["A"].width = 40
    agg.column_dimensions["B"].width = 100
    for c in agg[1]:
        c.font = Font(bold=True)

    return wb


def build_template(path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _build_workbook().save(path)
    return path


def build_template_bytes() -> bytes:
    buf = BytesIO()
    _build_workbook().save(buf)
    return buf.getvalue()

"""Wzorcowy zakres danych o defibrylatorach AED.

Wzorzec działania jest taki sam jak dla wykazu DGA (mcod.resources.dga_constants):
 * AED_COLUMNS            - układ kolumn zasobu pojedynczego dostawcy (wykazu AED),
 * MAIN_AED_COLUMNS       - układ kolumn zbiorczego wykazu ogólnopolskiego,
 * MAIN_AED_REQUIRED_SOURCE_COLUMNS - kolumny, które muszą mieć wartość, aby
   wiersz źródła trafił do zbiorczego wykazu.
"""

from typing import Dict, List

AED_RESOURCE_EXTENSIONS: List[str] = ["xlsx", "xls", "csv"]

COL_ID = "Identyfikator AED"
COL_LAT = "Szerokość geograficzna"
COL_LON = "Długość geograficzna"
COL_CITY = "Miejscowość"
COL_STREET = "Ulica i numer"
COL_TERYT = "Kod TERYT gminy"
COL_LOCATION = "Opis lokalizacji"
COL_OBJECT_TYPE = "Rodzaj obiektu"
COL_AVAILABILITY = "Dostępność"
COL_HOURS = "Godziny dostępności"
COL_ACCESS = "Sposób dostępu"
COL_STATUS = "Status urządzenia"
COL_VERIFIED = "Data ostatniej weryfikacji"
COL_CONTACT = "Kontakt instytucjonalny"

# Kolumna używana jako opis punktu (popup) na mapie portalu.
COL_LABEL_FOR_MAP = COL_STREET

# Układ kolumn zasobu dostawcy (kolejność ma znaczenie, jak w DGA).
AED_COLUMNS: List[str] = [
    "Lp.",
    COL_ID,
    COL_LAT,
    COL_LON,
    COL_CITY,
    COL_STREET,
    COL_TERYT,
    COL_LOCATION,
    COL_OBJECT_TYPE,
    COL_AVAILABILITY,
    COL_HOURS,
    COL_ACCESS,
    COL_STATUS,
    COL_VERIFIED,
    COL_CONTACT,
]

# Kolumny dopisywane przy agregacji - pozwalają wskazać dysponenta i zakres referencyjny źródła.
COL_PROVIDER = "Nazwa dysponenta zasobu"
COL_SCOPE = "Zakres referencyjny źródła"
COL_SOURCE_RESOURCE = "Identyfikator zasobu źródłowego"
COL_SOURCE_DATE = "Data aktualizacji zasobu źródłowego"

# Kolumny wyliczane przy scalaniu (nie występują w wykazie dostawcy).
COL_SOURCES_COUNT = "Liczba źródeł"
COL_OTHER_PROVIDERS = "Pozostali dysponenci"
COL_FRESHNESS = "Aktualność"
COL_DAYS_SINCE = "Dni od ostatniej weryfikacji"
COL_MERGE_CONF = "Pewność połączenia"
MERGE_CONF_NONE = (
    "nie dotyczy"  # zapisujemy tekstem („99%”), bo portal z pierwszych wierszy wnioskuje typ liczbowy i łamie go puste wartości
)
COL_TRUST = "Wiarygodność"
COL_NOTES = "Uwagi do danych"
COL_POSTAL = "Kod pocztowy"
COL_HOURS_NORM = "Godziny (znormalizowane)"

# Aktualność rekordu: weryfikacja nie starsza niż FRESH_DAYS = aktualny; do STALE_DAYS = do weryfikacji; starsza = nieaktualny.
FRESH_DAYS = 365
STALE_DAYS = 730
FRESHNESS_ACTUAL = "aktualny"
FRESHNESS_TO_VERIFY = "do weryfikacji"
FRESHNESS_STALE = "nieaktualny"
FRESHNESS_BROKEN = "nieczynny"

MAIN_AED_COLUMNS: List[str] = [
    "Lp.",
    COL_PROVIDER,
    COL_SCOPE,
    COL_SOURCE_RESOURCE,
    COL_SOURCE_DATE,
    COL_ID,
    COL_LAT,
    COL_LON,
    COL_CITY,
    COL_STREET,
    COL_TERYT,
    COL_LOCATION,
    COL_OBJECT_TYPE,
    COL_AVAILABILITY,
    COL_HOURS,
    COL_ACCESS,
    COL_STATUS,
    COL_VERIFIED,
    COL_CONTACT,
    COL_SOURCES_COUNT,
    COL_OTHER_PROVIDERS,
    COL_MERGE_CONF,
    COL_FRESHNESS,
    COL_DAYS_SINCE,
    COL_TRUST,
    COL_NOTES,
    COL_POSTAL,
    COL_HOURS_NORM,
]

# Raport scalania: jeden wiersz = jedna uwaga do wykazu dostawcy (odrzucony wiersz, połączony duplikat, pominięty zasób).
REPORT_COLUMNS: List[str] = [
    "Dysponent",
    "Zasób źródłowy",
    "Wiersz w pliku",
    "Identyfikator AED",
    "Wynik",
    "Powód",
]
REPORT_REJECTED = "odrzucono wiersz"
REPORT_MERGED = "połączono z innym dysponentem"
REPORT_SKIPPED = "pominięto zasób"
REPORT_OK = "brak uwag"
REPORT_NEW = "nowy rekord"
REPORT_REMOVED = "usunięto z wykazu zbiorczego"
REPORT_CHANGED = "zmieniony rekord"

MAIN_AED_REQUIRED_SOURCE_COLUMNS: List[str] = [
    COL_ID,
    COL_LAT,
    COL_LON,
    COL_AVAILABILITY,
    COL_ACCESS,
    COL_STATUS,
    COL_VERIFIED,
]

# Słowniki wartości (walidowane przy agregacji).
AVAILABILITY_VALUES: List[str] = ["całodobowo", "w godzinach", "ograniczona"]
ACCESS_VALUES: List[str] = ["swobodny", "za zgodą", "zamknięte na klucz"]
STATUS_VALUES: List[str] = ["czynny", "nieczynny", "do weryfikacji"]

ENUM_COLUMNS: Dict[str, List[str]] = {
    COL_AVAILABILITY: AVAILABILITY_VALUES,
    COL_ACCESS: ACCESS_VALUES,
    COL_STATUS: STATUS_VALUES,
}

# Przybliżony prostokąt otaczający Polskę (WGS84) - szybka kontrola błędnych współrzędnych.
POLAND_LAT_RANGE = (48.9, 55.0)
POLAND_LON_RANGE = (14.0, 24.2)

# Deduplikacja punktów RÓŻNYCH dysponentów. Do DEDUP_CERTAIN_METERS to na pewno to samo urządzenie.
# Od DEDUP_CERTAIN_METERS do DEDUP_MAX_METERS łączymy tylko, gdy opisy miejsca są podobne (co najmniej DEDUP_TEXT_MIN).
# Progi to nasze założenia (dokładność współrzędnych dysponentów bywa rzędu kilku-kilkunastu metrów).
DEDUP_CERTAIN_METERS = 10
DEDUP_MAX_METERS = 50
DEDUP_TEXT_MIN = 0.6

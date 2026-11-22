# Misja AED – instrukcja dla jury

> Wersja robocza: adresy i konta uzupełnimy po wdrożeniu publicznym prototypu.

## Idea w jednym zdaniu
Portal dane.gov.pl dostaje **wykaz AED** – nowy typ zasobu (wzorowany na wykazie DGA): każdy dysponent publikuje
własny wykaz w jednolitym układzie kolumn, a portal **codziennie scala je w jeden ogólnopolski wykaz**.
Dysponent nadal odpowiada za swoje dane; portal wskazuje dla każdego rekordu dysponenta i zakres referencyjny źródła.

## Gdzie sprawdzić wymagania z treści zadania

| # | Wymaganie | Gdzie |
|---|-----------|-------|
| 1 | Wzorcowy zakres danych (xlsx) | `aed-demo/wzorcowy-zakres-danych-AED.xlsx` (arkusze: wzór, opis kolumn, kolumny wykazu zbiorczego) |
| 2 | Dane z wielu rozproszonych źródeł ze wskazaniem zakresu referencyjnego | wykaz zbiorczy: kolumny „Nazwa dysponenta zasobu”, „Zakres referencyjny źródła”, „Data aktualizacji zasobu źródłowego” |
| 3 | Integracja informacji od wszystkich dysponentów w jednym zbiorze | zbiór „Ogólnopolski wykaz defibrylatorów AED – zbiór zbiorczy” |
| 4 | Format odczytywalny maszynowo | zasób zbiorczy w CSV; źródła csv/xls/xlsx |
| 5 | Zgodność z zasadami portalu | rozszerzenie istniejących mechanizmów portalu: flaga zasobu, walidacja w formularzu, zadanie Celery – patrz `backend/mcod/aed/` |
| 6 | Kod źródłowy | `backend/mcod/aed/`, zmiany w `backend/mcod/resources/` (forms, admin, models, migracja 0076) |

## Kroki dla dostawcy danych (panel administracyjny)
1. Zaloguj się do panelu administracyjnego jako dostawca.
2. Utwórz zbiór danych instytucji i dodaj zasób z plikiem csv/xls/xlsx w układzie z pliku wzorcowego.
3. Zaznacz „Wykaz defibrylatorów AED: Tak” i zapisz. Przy błędnych kolumnach formularz wskaże oczekiwane nazwy i kolejność.
4. Po zapisie wykaz trafia do wykazu zbiorczego przy najbliższym przebiegu zadania (codziennie) albo od razu po
   uruchomieniu komendy `python manage.py aed_build_main`.

## Konwerter: z dowolnego pliku do wzorca
Dysponenci mają dane w różnych układach, więc portal ma konwerter (panel administracyjny, adres `/aed/konwerter/`, albo komenda `manage.py aed_convert`).
1. Wgraj plik (csv, xlsx, xls, json/GeoJSON, także wynik zapytania Overpass z OpenStreetMap) i opcjonalnie wybierz profil źródła (`osm`).
2. Konwerter dopasowuje kolumny: profil, nazwa lub synonim, podobieństwo nazw, a na końcu zawartość kolumny (zakresy współrzędnych, daty, układ PL-1992).
3. Ujednolica wartości: współrzędne (przecinek, zapis stopniowy, WKT, PL-1992 → WGS84), „całą dobę" → `całodobowo`, „sprawny" → `czynny` itd.
4. Pokazuje mapowanie z poziomem pewności, podgląd i raport każdego wiersza (ok, poprawiono, odrzucono wraz z powodem). Wynik i raport można pobrać jako CSV.
5. Wynik wgrywasz jako zasób z flagą „Wykaz defibrylatorów AED".

Zasady: **działa na jawnych regułach, bez AI**, więc wynik jest powtarzalny i nie wymaga instalowania modeli. Czego źródło nie podaje (np. daty weryfikacji), konwerter **nie zgaduje**:
trzeba to wpisać jawnie, inaczej wiersz jest odrzucany. Dla układu PL-1992 kolejność osi nie da się wiarygodnie odgadnąć, więc przyjmujemy „pierwsza kolumna = wschód" i zaznaczamy to w raporcie (jest opcja odwrócenia).
Pliki przykładowe (syntetyczne): `backend/mcod/aed/demo_data/przyklad-inne-kolumny.csv` (inne nazwy kolumn, PL-1992, daty dd.mm.rrrr) i `przyklad-osm-overpass-SYNTETYCZNE.json` (format Overpass, profil `osm`).
Prawdziwe dane z OSM pobierzesz zapytaniem Overpass `[out:json][timeout:60];area["ISO3166-1"="PL"][admin_level=2]->.pl;node["emergency"="defibrillator"](area.pl);out;`.
OSM ma licencję ODbL (share-alike): taki wykaz publikujemy osobno, nie mieszamy go ze zbiorem na CC BY.

## Co dzieje się podczas scalania
- odrzucane są pojedyncze błędne wiersze (współrzędne poza Polską, niedozwolone wartości słownikowe, zła data), a nie cały wykaz,
- duplikaty (ten sam AED u kilku dysponentów, odległość ≤ 25 m) są łączone; kolumna „Liczba źródeł” pokazuje ile wykazów go zgłosiło,
- w zbiorczym zostaje rekord ze statusem „czynny” i najświeższą weryfikacją.

## Dane demonstracyjne
Pliki w `backend/mcod/aed/demo_data/` (generator: `aed-demo/generate_demo.py`) są **syntetyczne** (fikcyjni dysponenci, identyfikatory DEMO-*). Zawierają celowe błędy, żeby pokazać walidację
i deduplikację: 14 wierszy wejściowych → 2 odrzucone → 1 duplikat → 11 rekordów w wykazie zbiorczym.

## Wykorzystanie AI
Kod i dokumentację przygotowywano z pomocą asystenta AI (Claude Code). Analizę wymagań, decyzje projektowe i weryfikację wyników wykonał zespół.

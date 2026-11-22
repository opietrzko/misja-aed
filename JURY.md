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

## Licencja
Zbiór zbiorczy jest udostępniany na **CC BY 4.0** (uznanie autorstwa): wolna i otwarta, pozwala na użycie komercyjne i przetwarzanie, a nazwa dysponenta
zostaje przy danych w kolumnach „Nazwa dysponenta zasobu" i „Zakres referencyjny źródła". Licencję ustawia kod przy każdym scaleniu (`ensure_main_dataset_license`).

Zasady wobec źródeł o innych warunkach (rekomendacja, nie opinia prawna):
- do zbioru zbiorczego trafiają wykazy na licencji nie ostrzejszej niż CC BY (CC0, CC BY, dane publiczne),
- licencje NC (zakaz użycia komercyjnego) i ND (zakaz przetwarzania) wykluczamy: nie są wolne i uniemożliwiają łączenie danych,
- licencji SA nie stosujemy w zbiorze zbiorczym, bo wymusza tę samą licencję na wynikach,
- **OpenStreetMap (ODbL, share-alike)** nie może wejść do zbioru na CC BY: publikujemy go jako osobny wykaz na licencji zgodnej z ODbL
  (do uzgodnienia z organizatorem).

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
- duplikaty (ten sam AED u **różnych** dysponentów, odległość ≤ 25 m) są łączone, a w zbiorczym zostaje rekord ze statusem „czynny” i najświeższą weryfikacją.
  Kolumna „Liczba źródeł” pokazuje, ile wykazów go zgłosiło, a „Pozostali dysponenci” wymienia pozostałych w formie „Dysponent (identyfikator)”.
  Dwa urządzenia **jednego** dysponenta blisko siebie (np. w dużym budynku) nie są łączone,
- każdy rekord dostaje **Aktualność** i „Dni od ostatniej weryfikacji”: `nieczynny` (status), `nieaktualny` (weryfikacja starsza niż 2 lata),
  `do weryfikacji` (starsza niż rok, status „do weryfikacji” albo data z przyszłości), `aktualny` (czynny i zweryfikowany w ciągu roku),
- zasób zbiorczy jest **aktualizowany w miejscu**: ma stały identyfikator i adres, więc linki i zakładki nie psują się po każdym scaleniu
  (dane, schemat mapy i indeks wyszukiwarki odświeża portal tak jak przy ręcznej zmianie pliku w panelu),
- zasoby wykazów AED można filtrować w API: `/1.4/resources?contains_aed_list=true` oraz `/1.4/search?contains_aed_list=true`.

## Dostawcy publikujący przez harvester (XML i CKAN)
Wykaz AED nie wymaga ręcznego klikania w panelu. Instytucja, która zasila portal harvesterem, oznacza zasób flagą i dostaje tę samą walidację co w formularzu:
- **XML:** nowy schemat **1.14** (`containsAedList`, element opcjonalny, starsze wersje działają bez zmian). Schemat zasobu sprawdza: plik csv/xls/xlsx pod adresem `url`,
  wzorcowe kolumny, brak jednoczesnej flagi DGA, co najwyżej jeden wykaz w pliku i brak innego wykazu instytucji dodanego inną drogą.
- **CKAN:** pole zasobu `contains_aed_list`. Import częściowy odrzuca zbiór z błędnym wykazem i opisuje powód w szczegółach importu w panelu.
Ograniczenie: w imporcie CKAN nie sprawdzamy jeszcze, czy instytucja ma już wykaz dodany inną drogą (w XML sprawdzamy).

## Dane demonstracyjne
Pliki w `backend/mcod/aed/demo_data/` (generator: `aed-demo/generate_demo.py`) są **syntetyczne** (fikcyjni dysponenci, identyfikatory DEMO-*). Zawierają celowe błędy, żeby pokazać walidację
i deduplikację: 14 wierszy wejściowych → 2 odrzucone → 1 duplikat → 11 rekordów w wykazie zbiorczym.

## Wykorzystanie AI
Kod i dokumentację przygotowywano z pomocą asystenta AI (Claude Code). Analizę wymagań, decyzje projektowe i weryfikację wyników wykonał zespół.

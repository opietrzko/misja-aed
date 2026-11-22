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
- duplikaty (ten sam AED u **różnych** dysponentów) są łączone: zawsze do 10 m, a do 50 m tylko przy podobnym adresie. Zostaje rekord ze statusem „czynny”,
  najświeższą weryfikacją i najpełniejszym opisem. Kolumna „Liczba źródeł” pokazuje, ile wykazów go zgłosiło, „Pozostali dysponenci” wymienia pozostałych
  („Dysponent (identyfikator)”), a „Pewność połączenia” (np. „99%”, „nie dotyczy” bez połączeń) wynika z odległości i podobieństwa adresu. Dwa urządzenia **jednego** dysponenta blisko siebie
  (np. w dużym budynku) nie są łączone, a różne numery budynków („Floriańska 1” i „Floriańska 10”) nigdy nie są uznane za to samo miejsce,
- każdy rekord dostaje **Aktualność** i „Dni od ostatniej weryfikacji”: `nieczynny` (status), `nieaktualny` (weryfikacja starsza niż 2 lata),
  `do weryfikacji` (starsza niż rok, status „do weryfikacji” albo data z przyszłości), `aktualny` (czynny i zweryfikowany w ciągu roku),
- zasób zbiorczy jest **aktualizowany w miejscu**: ma stały identyfikator i adres, więc linki i zakładki nie psują się po każdym scaleniu
  (dane, schemat mapy i indeks wyszukiwarki odświeża portal tak jak przy ręcznej zmianie pliku w panelu),
- zasoby wykazów AED można filtrować w API: `/1.4/resources?contains_aed_list=true` oraz `/1.4/search?contains_aed_list=true`.

## Algorytmy (jawne reguły, bez AI)
Wszystko deterministyczne, na pandas i bibliotece standardowej, bez nowych zależności. **Progi i wagi poniżej to nasze założenia do dostrojenia, nie wiedza ekspercka.**
- **Wiarygodność rekordu (0-100)** = kompletność opisu (do 30) + aktualność weryfikacji (do 30; „do weryfikacji” w połowie) + potwierdzenie przez innych dysponentów
  (2 źródła = 15, 3 i więcej = 20) + dokładność współrzędnych (5 miejsc po przecinku = 10, 4 = 7, 3 = 3) + godziny w zapisie maszynowym (10),
  minus 10 za każdą flagę anomalii. Urządzenie „nieczynne” dostaje najwyżej 20. Kolumny „Wiarygodność” i „Uwagi do danych”.
- **Flagi anomalii:** niska precyzja współrzędnych (≤ 3 miejsca po przecinku to ok. 100 m i gorzej), co najmniej 3 rekordy jednego dysponenta w identycznym punkcie
  (podejrzany „środek miasta”), data weryfikacji z przyszłości, nierozpoznane godziny.
- **Parser godzin:** z „pn–pt 7:30–16:00”, „Mo-Fr 08:00-18:00”, „godz: 8.00-18.00 w dni robocze”, „od 8 do 16 codziennie”, „pn-pt 7-17, sob 9-13” robi jednolity
  zapis (`Mo-Fr 07:30-16:00; Sa 09:00-13:00`, `24/7`). Nie zgaduje: godziny bez dni, niepoprawne albo nakładające się przedziały zostają nierozpoznane (kolumna
  „Godziny (znormalizowane)” pusta i flaga w uwagach).
- **Adresy:** „ulica Paradna 36, 93-345 Łódź” → „ul. Paradna 36”, miejscowość „Łódź” (gdy nie podano jej osobno), kod „93-345” w osobnej kolumnie. Konwerter uzupełnia
  miejscowość z adresu. Kod pocztowy bez myślnika nie jest rozpoznawany (łatwo go pomylić z numerem budynku).
- **Wykrywanie zmian między scaleniami** w raporcie: nowe, usunięte i zmienione rekordy (status, dostępność, sposób dostępu, data weryfikacji, współrzędne) z opisem
  „przed → po”, po kluczu (dysponent, identyfikator).

## Dostawcy publikujący przez harvester (XML i CKAN)
Wykaz AED nie wymaga ręcznego klikania w panelu. Instytucja, która zasila portal harvesterem, oznacza zasób flagą i dostaje tę samą walidację co w formularzu:
- **XML:** nowy schemat **1.14** (`containsAedList`, element opcjonalny, starsze wersje działają bez zmian). Schemat zasobu sprawdza: plik csv/xls/xlsx pod adresem `url`,
  wzorcowe kolumny, brak jednoczesnej flagi DGA, co najwyżej jeden wykaz w pliku i brak innego wykazu instytucji dodanego inną drogą.
- **CKAN:** pole zasobu `contains_aed_list`. Import częściowy odrzuca zbiór z błędnym wykazem i opisuje powód w szczegółach importu w panelu.
Ograniczenie: w imporcie CKAN nie sprawdzamy jeszcze, czy instytucja ma już wykaz dodany inną drogą (w XML sprawdzamy).

## Ograniczenia
Lista do slajdu „ograniczenia" (stan na dziś, uczciwie):
- **Zakres zmian w portalu (założenie).** Nie mogliśmy potwierdzić z organizatorem, jak szeroko wolno rozszerzać kod portalu. Oparliśmy się na wskazówce mentora z czatu
  hackathonu, że trzeba „dostosować i przebudować logikę i metody w portalu”, aby wykazy można było pobierać i scalać w jedną standardową listę, oraz na jego zastrzeżeniu, że
  nie wolno zmieniać zasad publikacji (za dane odpowiada dostawca, a nie portal). Zmiany w istniejącym kodzie są addytywne: 18 plików, +274 / −2 linie, **zero nowych zależności**,
  ten sam stos (Django, Celery, Elasticsearch, pandas i pyproj, które portal już ma). Nowy kod jest w module `mcod/aed`. Najbardziej „zewnętrzne” elementy to schemat XSD harvestera 1.14
  (opcjonalny element, starsze wersje działają bez zmian), poprawka frontu Leaflet (obejście błędu serwera deweloperskiego) i `host-gateway` w docker-compose (tylko środowisko lokalne).
- **Brak geokodowania adresów w środowisku lokalnym.** Konwerter wymaga współrzędnych i nie zgaduje ich z adresu. Portal dane.gov.pl ma własny geokoder i potrafi wyliczyć punkty
  z adresów (miejscowość, kod pocztowy, ulica, numer), ale jego usługi (`GEOCODER_URL`) nie ma w repozytorium ani w naszym środowisku. Przykład z praktyki: prawdziwy wykaz z Łodzi
  (140 adresów, bez współrzędnych) jest przez konwerter odrzucany z komunikatem „brak współrzędnych (jest adres)". Rozwiązania spoza naszego środowiska: współrzędne od dysponenta
  albo geokoder portalu. Zewnętrzne geokodowanie (np. z OpenStreetMap) odrzuciliśmy ze względu na licencję (ODbL, share-alike, niezgodna ze zbiorem na CC BY).
- **Dane demonstracyjne są syntetyczne** (fikcyjni dysponenci). Konwerter nie był testowany na szerokim zestawie prawdziwych plików, poza jednym wykazem z Łodzi.
- **Licencje źródeł.** OpenStreetMap (ODbL) publikujemy osobno, a nie w zbiorze zbiorczym. Dane PRG (GUGiK) są „bezpłatne i do dowolnego wykorzystania" z podaniem źródła, ale bez nazwanej licencji. To rekomendacje, a nie opinia prawna.
- **Deduplikacja jest heurystyką** (odległość do 10 m, do 50 m przy podobnym adresie). Gdy dysponent ma dwa urządzenia blisko jednego cudzego, oba mogą zostać do niego dołączone.
- **Aktualność, wiarygodność i dedup:** progi 12 i 24 miesięcy, wagi wiarygodności oraz promienie 10 i 50 m to nasze propozycje, nie wymóg.
- **PL-1992:** kolejność osi nie da się wiarygodnie odgadnąć, więc przyjmujemy „pierwsza kolumna = wschód" i zaznaczamy to w raporcie (jest przełącznik).
- **Import CKAN** nie sprawdza, czy instytucja ma już wykaz AED dodany inną drogą (XML sprawdza). Walidatory XML i CKAN sprawdzone na przykładowych danych, nie na pełnym imporcie harvestera.
- **Harmonogram** codziennego scalania jest w kodzie (Celery beat), ale lokalnie nie jest uruchomiony. Scalanie uruchamialiśmy ręcznie komendą `aed_build_main`.
- **Dostępność i telefon.** Strona konwertera przeszła kontrole statyczne (etykiety pól, opisy i nagłówki tabel, unikalne identyfikatory, kontrast kolorów AA, najniższy 4,92). Szablon panelu administracyjnego portalu nie ma jednak meta viewport i nie jest responsywny
  (dodaliśmy viewport tylko do naszej strony). Wyglądu na prawdziwym telefonie nie sprawdzaliśmy.
- **Nie zweryfikowane:** pełny przebieg istniejących testów portalu (sprawdzone wybrane, patrz wyniki w opisie projektu) oraz walidatory XML i CKAN na pełnym imporcie harvestera.

## Dane demonstracyjne
Pliki w `backend/mcod/aed/demo_data/` (generator: `aed-demo/generate_demo.py`) są **syntetyczne** (fikcyjni dysponenci, identyfikatory DEMO-*). Zawierają celowe błędy, żeby pokazać walidację
i deduplikację: 14 wierszy wejściowych → 2 odrzucone → 1 duplikat → 11 rekordów w wykazie zbiorczym.

## Wykorzystanie AI
Pełny opis w [`README.md`](README.md#wykorzystanie-sztucznej-inteligencji). W skrócie: kod, testy i dokumentację przygotowano z pomocą Claude (Claude Code) pod kierunkiem zespołu,
a identyfikację wizualną wykonano w programie Affinity z pomocą Claude (przez MCP) na podstawie poleceń zespołu. Koncepcja, nazwa, decyzje projektowe i weryfikacja wyników: zespół.
W działaniu prototypu AI nie występuje (jawne reguły).

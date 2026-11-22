# Misja AED - instrukcja dla jury

> **Prototyp online: [aed.haloware.pl](https://aed.haloware.pl).** Uruchomienie lokalne krok po kroku: [`README.md`](README.md#pierwsze-kroki).

## Idea w jednym zdaniu
Portal dane.gov.pl dostaje **wykaz AED** - nowy typ zasobu (wzorowany na wykazie DGA): każdy dysponent publikuje
własny wykaz w jednolitym układzie kolumn, a portal **codziennie scala je w jeden ogólnopolski wykaz**.
Dysponent nadal odpowiada za swoje dane; portal wskazuje dla każdego rekordu dysponenta i zakres referencyjny źródła.

Jak przetestować całość krok po kroku: [`TESTOWANIE.md`](TESTOWANIE.md). Pliki do ręcznego testu: [`przykladowe-dane/`](przykladowe-dane/).

## Szybka ścieżka (3 minuty)
1. **Zobacz, że działa:** [aed.haloware.pl](https://aed.haloware.pl), wyszukaj „AED” i otwórz „Ogólnopolski wykaz defibrylatorów AED - zbiór zbiorczy”. Tabela z danymi od kilku dysponentów, zakładka **Mapa**, pobranie CSV i GeoJSON.
2. **Zaloguj się do panelu:** [admin.aed.haloware.pl](https://admin.aed.haloware.pl), login w sekcji „Konto administratora do testów” poniżej, hasło w zgłoszeniu.
3. **Wrzuć dane:** Zasoby, Dodaj, wybierz zbiór instytucji, która nie ma jeszcze wykazu (trzy demonstracyjne już go mają), wgraj [`wcr-demo-gdansk.csv`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/01-wykazy-dostawcow/wcr-demo-gdansk.csv) i zaznacz **„Wykaz defibrylatorów AED: Tak”**. Wgranie pliku w złym układzie kolumn ([`zle-kolumny.csv`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/03-pliki-odrzucane/zle-kolumny.csv)) jest odrzucane z podpowiedzią.
4. **Zobacz, że dane są zwracane:** nowy zasób jest na stronie portalu i w API: [`/1.4/resources?contains_aed_list=true`](https://api.aed.haloware.pl/1.4/resources?contains_aed_list=true) (po dodaniu wykaz jest o jeden więcej niż wcześniej). Do zbioru zbiorczego trafia przy codziennym scalaniu (03:45), a efekt scalania na danych demonstracyjnych widać już w jego raporcie.

Po teście usuń swój zasób. Pliki do testów są w [`przykladowe-dane/`](przykladowe-dane/) w repozytorium (syntetyczne, z opisem oczekiwanych wyników).

## Pełna ścieżka (opcjonalnie, dla chcących sprawdzić więcej)
Tabela, mapa, licencja, konwerter z innych układów, walidacja, harvester i kod. Szczegóły:


**A. Efekt dla użytkownika (bez logowania)**
1. Otwórz [aed.haloware.pl](https://aed.haloware.pl) i wyszukaj „AED”. Zobaczysz 3 wykazy dysponentów i zbiór „Ogólnopolski wykaz defibrylatorów AED - zbiór zbiorczy”.
2. Otwórz zbiór zbiorczy, a w nim zasób z wykazem (CSV). Tabela ma kolumny jak wzorzec oraz **Aktualność**, **Wiarygodność**, „Nazwa dysponenta zasobu”, „Zakres referencyjny źródła”. Zakładka **Mapa** pokazuje punkty.
3. Sprawdź licencję (CC BY 4.0, sekcja „Warunki wykorzystywania”) oraz pozostałe zasoby zbioru: **GeoJSON** i **raport scalania** (odrzucone wiersze z powodem, połączone duplikaty).
4. API: [lista wykazów AED](https://api.aed.haloware.pl/1.4/resources?contains_aed_list=true).
   Oczekiwane: 4 zasoby (3 wykazy dysponentów i zbiorczy).

**B. Zalogowanie do panelu**
5. Wejdź na [admin.aed.haloware.pl](https://admin.aed.haloware.pl) i zaloguj się kontem z sekcji „Konto administratora do testów” poniżej.

**C. Wykaz jako zasób portalu**
6. W panelu: Zasoby, otwórz „Wykaz AED - AED w Gdańsku i okolicach”. Pole **„Wykaz defibrylatorów AED”** ustawione na „Tak” to nasza flaga zasobu (obok istniejącej flagi wykazu DGA).

**D. Dodanie własnego wykazu (zasilanie ręczne)**
7. Pobierz plik wzorcowy: [`wzorcowy-zakres-danych-AED.xlsx`](aed-demo/wzorcowy-zakres-danych-AED.xlsx) (jest też przyciskiem na górze strony konwertera).
8. Utwórz zbiór danych dla instytucji, która nie ma jeszcze wykazu, i dodaj zasób z plikiem z [`01-wykazy-dostawcow/`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/01-wykazy-dostawcow) albo [`wspolrzedne-poza-polska.csv`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/03-pliki-odrzucane/wspolrzedne-poza-polska.csv). Zaznacz „Wykaz defibrylatorów AED: Tak” i zapisz.
   Instytucja może mieć tylko jeden wykaz, więc trzy instytucje demonstracyjne (Urząd Miasta Demo-Kraków, Fundacja Demo-Ratownik, WCR Demo-Gdańsk) już go mają. Użyj innej instytucji. Po teście usuń zasób.
9. **Walidacja:** wgraj [`zle-kolumny.csv`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/03-pliki-odrzucane/zle-kolumny.csv). Oczekiwane: formularz odrzuca plik i wskazuje oczekiwane nazwy i kolejność kolumn.

**E. Konwerter (dane w innym układzie niż wzorzec)**
10. Otwórz [konwerter](https://admin.aed.haloware.pl/aed/konwerter/) i wgraj pliki z [`02-konwerter/`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/02-konwerter). Ustawienia i oczekiwane wyniki każdego pliku (np. „3 z 4”) są w README tego folderu.
11. Sprawdź mapowanie kolumn z poziomem pewności, podgląd i raport wierszy z powodem odrzucenia. Pobierz wynik jako CSV i wgraj go jak w kroku 8.
12. Plik [`tylko-adresy-bez-wspolrzednych.csv`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/03-pliki-odrzucane/tylko-adresy-bez-wspolrzednych.csv) ma zostać odrzucony w całości (konwerter nie zgaduje współrzędnych z adresu).

**F. Zasilanie automatyczne**
13. Scalanie wykazów w zbiorczy robi zadanie Celery **codziennie o 03:45** (`mcod/celeryapp.py`), więc własny wykaz z kroku 8 pojawi się w zbiorze zbiorczym następnego dnia. Z panelu nie da się go uruchomić ręcznie (to komenda `aed_build_main` na serwerze). Przebieg scalania na danych demonstracyjnych (14 wierszy, 2 odrzucone, 1 duplikat, 11 rekordów) widać już w raporcie scalania z kroku 3.
14. Import przez harvester: przykład pliku XML w schemacie 1.14 jest w [`05-import-xml/`](https://github.com/opietrzko/misja-aed/blob/main/przykladowe-dane/05-import-xml). Pełnego importu przez źródło danych nie sprawdzaliśmy (patrz „Ograniczenia”).

Instrukcja uruchomienia całości lokalnie i testów automatycznych: [`TESTOWANIE.md`](TESTOWANIE.md).

## Gdzie sprawdzić wymagania z treści zadania

| # | Wymaganie | Gdzie |
|---|-----------|-------|
| 1 | Wzorcowy zakres danych (xlsx) | `aed-demo/wzorcowy-zakres-danych-AED.xlsx` (arkusze: wzór, opis kolumn, kolumny wykazu zbiorczego) |
| 2 | Dane z wielu rozproszonych źródeł ze wskazaniem zakresu referencyjnego | wykaz zbiorczy: kolumny „Nazwa dysponenta zasobu”, „Zakres referencyjny źródła”, „Data aktualizacji zasobu źródłowego” |
| 3 | Integracja informacji od wszystkich dysponentów w jednym zbiorze | zbiór „Ogólnopolski wykaz defibrylatorów AED - zbiór zbiorczy” |
| 4 | Format odczytywalny maszynowo | zasób zbiorczy w CSV i w GeoJSON, raport scalania w CSV; źródła csv/xls/xlsx |
| 5 | Zgodność z zasadami portalu | rozszerzenie istniejących mechanizmów portalu: flaga zasobu, walidacja w formularzu, zadanie Celery - patrz `backend/mcod/aed/` |
| 6 | Kod źródłowy | nowy moduł `backend/mcod/aed/`; zmiany w istniejących plikach: `resources` (forms, admin, models, migracja 0076, API i indeks), `harvester`, `search`, `settings`, `celeryapp`; pełna lista w `backend/CHANGELOG.md` |
| 7 | Nazwa akcji, hasło i logotyp | nazwa „Przez dane do serca”, hasło „Zdążysz, jeśli wiesz gdzie.”; logotyp w JPG, PNG, PDF i SVG w `identyfikacja-wizualna/` |
| 8 | Księga znaku (PDF) | `identyfikacja-wizualna/ksiega-znaku.pdf`: koncepcja (4 zdania), kolorystyka, pole ochronne, minimalna wielkość, niedozwolone użycia, typografia, wersje znaku, zastosowania |
| 9 | Zachęcenie dysponentów do dzielenia się danymi | `identyfikacja-wizualna/materialy/`: plakat A3, naklejka „Ten AED jest w bazie” z kodem QR, baner dla dane.gov.pl, post, animowane logo (SVG); komunikaty do dysponentów w księdze znaku |

## Konto administratora do testów (prototyp online)
Na wersji online przygotowaliśmy konto administracyjne tylko dla jury. Pozwala wejść do panelu, dodać wykaz, uruchomić konwerter i obejrzeć zbiór zbiorczy.

| Pole | Wartość |
|---|---|
| Panel administracyjny | https://admin.aed.haloware.pl |
| Konwerter AED | https://admin.aed.haloware.pl/aed/konwerter/ |
| Login (e-mail) | `jury@aed.haloware.pl` |
| Hasło | (podane w zgłoszeniu konkursowym) |
| Rola | administrator (superużytkownik) |

Środowisko demonstracyjne z danymi syntetycznymi, bez prawdziwych danych. Konto zostanie usunięte po zakończeniu oceny.

## Kroki dla dostawcy danych (panel administracyjny)
1. Zaloguj się do panelu administracyjnego. Na wersji online: konto z sekcji „Konto administratora do testów” powyżej. W środowisku lokalnym: `pelnomocnik@mcod.local` (hasło `User123!`) jako dostawca albo `admin@mcod.local` (`testadmin123!`) jako administrator. Konta deweloperskie, tylko dane testowe.
2. Utwórz zbiór danych instytucji i dodaj zasób z plikiem csv/xls/xlsx w układzie z pliku wzorcowego.
3. Zaznacz „Wykaz defibrylatorów AED: Tak” i zapisz. Przy błędnych kolumnach formularz wskaże oczekiwane nazwy i kolejność.
4. Po zapisie wykaz trafia do wykazu zbiorczego przy najbliższym przebiegu zadania (codziennie) albo od razu po
   uruchomieniu komendy `python manage.py aed_build_main`.

## Jak korzystać z danych (ratownik, urzędnik, każdy)
Użytkownikiem zbioru są służby ratownicze, ale także każdy, kto szuka najbliższego AED lub chce użyć danych we własnej aplikacji.
1. Na stronie portalu wyszukaj zbiór „Ogólnopolski wykaz defibrylatorów AED - zbiór zbiorczy” i otwórz go.
2. W zasobie zbiorczym zobacz tabelę (kolumny **Aktualność** i **Wiarygodność** mówią, czy punktowi można ufać) albo zakładkę **Mapa** z punktami AED.
3. Sprawdź warunki użycia: licencja CC BY 4.0 (sekcja „Warunki wykorzystywania”).
4. Pobierz dane maszynowo: **CSV** lub **GeoJSON** (trzeci zasób w zbiorze), albo użyj API: `/1.4/resources?contains_aed_list=true` (lista wykazów) i `/1.4/resources/<id>/geo` (punkty mapy).
5. Zobacz, kto jest dysponentem punktu i jaki jest zakres referencyjny źródła (kolumny „Nazwa dysponenta zasobu” i „Zakres referencyjny źródła”). Raport z ostatniego scalenia pokazuje odrzucone wiersze i zmiany.

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
1. Wgraj plik (csv, xlsx, xls, json/GeoJSON, także wynik zapytania Overpass z OpenStreetMap) i opcjonalnie wybierz profil źródła (`osm`). Na górze strony jest przycisk pobrania wzorcowego pliku (xlsx).
2. Konwerter dopasowuje kolumny: profil, nazwa lub synonim, podobieństwo nazw, a na końcu zawartość kolumny (zakresy współrzędnych, daty, układ PL-1992).
3. Ujednolica wartości: współrzędne (przecinek, zapis stopniowy, WKT, PL-1992 → WGS84), „całą dobę" → `całodobowo`, „sprawny" → `czynny` itd.
4. Pokazuje mapowanie z poziomem pewności, podgląd i raport każdego wiersza (ok, poprawiono, odrzucono wraz z powodem). Wynik i raport można pobrać jako CSV.
5. Wynik wgrywasz jako zasób z flagą „Wykaz defibrylatorów AED".

Zasady: **działa na jawnych regułach, bez AI**, więc wynik jest powtarzalny i nie wymaga instalowania modeli. Czego źródło nie podaje (np. daty weryfikacji), konwerter **nie zgaduje**:
trzeba to wpisać jawnie, inaczej wiersz jest odrzucany. Dla układu PL-1992 kolejność osi nie da się wiarygodnie odgadnąć, więc przyjmujemy „pierwsza kolumna = wschód" i zaznaczamy to w raporcie (jest opcja odwrócenia).
Pliki przykładowe (syntetyczne) są w `przykladowe-dane/02-konwerter/` (inne nazwy kolumn z PL-1992, format Overpass z profilem `osm`, xlsx z polskimi nagłówkami i literówkami, współrzędne w jednej kolumnie); README folderu podaje oczekiwany wynik każdego pliku.
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
- po każdym scaleniu w tym samym zbiorze powstają też **raport scalania** (CSV: odrzucone wiersze z numerem wiersza i powodem, połączone duplikaty, pominięte zasoby, zmiany od poprzedniego scalenia) oraz ten sam wykaz w **GeoJSON**,
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
- **Parser godzin:** z „pn-pt 7:30-16:00”, „Mo-Fr 08:00-18:00”, „godz: 8.00-18.00 w dni robocze”, „od 8 do 16 codziennie”, „pn-pt 7-17, sob 9-13” robi jednolity
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

## Zasady UX
Dla dostawcy danych droga od pliku do wykazu jest krótka i przewidywalna: wzorcowy plik xlsx pobiera się jednym przyciskiem na górze strony konwertera, a formularz zasobu przy błędnych kolumnach wskazuje oczekiwane nazwy i kolejność.
Konwerter pokazuje mapowanie kolumn z poziomem pewności, podgląd wyniku i raport każdego wiersza z powodem odrzucenia, a pola formularza mają etykiety i podpowiedzi (np. jaką datę podać). Niczego nie zgaduje, zamiast tego jasno mówi, co trzeba uzupełnić.
Użytkownik końcowy dostaje dane w tabeli, na mapie i w formatach maszynowych, z oceną aktualności i wiarygodności przy każdym punkcie. Dostępności i responsywności dotyczy punkt „Dostępność i telefon” w ograniczeniach poniżej.

## Ograniczenia
Lista do slajdu „ograniczenia" (stan na dziś, uczciwie):
- **Zakres zmian w portalu (założenie).** Nie mogliśmy potwierdzić z organizatorem, jak szeroko wolno rozszerzać kod portalu. Oparliśmy się na wskazówce mentora z czatu
  hackathonu, że trzeba „dostosować i przebudować logikę i metody w portalu”, aby wykazy można było pobierać i scalać w jedną standardową listę, oraz na jego zastrzeżeniu, że
  nie wolno zmieniać zasad publikacji (za dane odpowiada dostawca, a nie portal). Zmiany w istniejącym kodzie są addytywne: 18 plików, +277 / -5 linii, **zero nowych zależności**,
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
- **Dostępność i telefon.** Strona konwertera przeszła kontrole statyczne (etykiety pól, opisy i nagłówki tabel, unikalne identyfikatory, kontrast kolorów AA, najniższy 4,92). Powłoka panelu
  administracyjnego portalu ma sztywne body 960 px i nie jest responsywna, więc **na naszej stronie** zwalniamy szerokość i układamy menu pod treścią na wąskich ekranach. Sprawdzone w emulacji
  telefonu (375 px), tabletu (768 px) i desktopu na statycznej kopii strony z prawdziwymi stylami panelu: brak poziomego przewijania, tabele przewijają się w kontenerach. Pozostałe strony panelu
  (m.in. formularz zasobu z naszym polem) zostają takie, jakie są w portalu. Prawdziwego telefonu i działającego panelu (certyfikat) nie sprawdzaliśmy.
- **Testy.** Nasze: 156 testów logiki AED (w tym zgodność przykładowych danych z ich opisami) i 6 testów walidacji zdalnego wykazu; instrukcja w `TESTOWANIE.md`. Istniejące testy portalu uruchomiliśmy w wybranych grupach: harvester (schematy, serializery, CKAN, XML) bez porażek po
  jednej poprawce wzorca, zasoby, formularz, modele, DGA, indeksowanie i wyszukiwarka (139 testów) oraz komponent API (216 testów), wszystkie zielone. **Nie uruchamialiśmy pełnego zestawu** (m.in. CMS, raporty,
  użytkownicy) ani pełnego importu XML i CKAN. `makemigrations --check` zgłasza migrację w aplikacji `users` (`last_logged_method`), niezwiązaną z naszymi zmianami.

## Dane demonstracyjne
Folder `przykladowe-dane/` (generator: `aed-demo/generate_demo.py`; kopie wykazów dostawców w `backend/mcod/aed/demo_data/` dla komendy `aed_seed_demo`) jest **syntetyczny** (fikcyjni dysponenci, identyfikatory DEMO-*). Zawiera celowe błędy, żeby pokazać walidację
i deduplikację: 14 wierszy wejściowych → 2 odrzucone → 1 duplikat → 11 rekordów w wykazie zbiorczym.

## Wykorzystanie AI
Pełny opis w [`README.md`](README.md#wykorzystanie-sztucznej-inteligencji). W skrócie: kod, testy i dokumentację przygotowano z pomocą Claude (Claude Code) pod kierunkiem zespołu,
a identyfikację wizualną wykonano w programie Affinity z pomocą Claude (przez MCP) na podstawie poleceń zespołu. Koncepcja, nazwa, decyzje projektowe i weryfikacja wyników: zespół.
W działaniu prototypu AI nie występuje (jawne reguły).

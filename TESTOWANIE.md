# Jak testować Misję AED

Wszystkie komendy były uruchomione w trakcie prac. Gdzie czegoś nie sprawdzaliśmy, jest to napisane wprost (sekcja 3).
Dane do ręcznych testów: [`przykladowe-dane/`](przykladowe-dane/) (każdy podfolder ma README z oczekiwanym wynikiem).

## 0. Wymagania
- Środowisko z `README.md` (kontenery, front na porcie 4200, wpis w `/etc/hosts`). Certyfikat jest samopodpisany, więc przeglądarka ostrzeże.
- Konto deweloperskie do panelu administracyjnego: dane w `backend/README.md` (sekcja o panelu).
- Do testów automatycznych logiki: Python 3 i venv (krok 1.1).

## 1. Testy automatyczne

### 1.1 Logika AED (bez Dockera, kilka sekund)
Z katalogu `backend/`, jednorazowo:
```
python3 -m venv .venv
.venv/bin/pip install pandas pytest openpyxl pyproj xmlschema
```
Uruchomienie:
```
PYTHONPATH=. .venv/bin/python -m pytest mcod/aed/tests -c /dev/null --confcutdir=mcod/aed/tests --rootdir=. --ignore=mcod/aed/tests/test_remote_check.py -q
```
Oczekiwane: **156 testów, wszystkie zielone**. Obejmują: walidację i scalanie, deduplikację, wiarygodność i anomalie, parser godzin, adresy, konwerter,
wykrywanie zmian oraz zgodność folderu `przykladowe-dane/` z opisami w jego README. Bez `xmlschema` jeden test (walidacja XML) jest pomijany.
W kontenerze testy z `przykladowe-dane/` są pomijane (folder leży poza `backend/`).

### 1.2 Walidacja zdalnego wykazu (wymaga Django, więc w kontenerze)
```
docker exec mcod-admin python -c "import django,unittest; django.setup(); unittest.main(module='mcod.aed.tests.test_remote_check', argv=['x','-v'], exit=False)"
```
Oczekiwane: `Ran 6 tests ... OK`.

### 1.3 Istniejące testy portalu (ciężkie, najlepiej na VPS)
Z katalogu `backend/`. Pomijamy entrypoint i kompilujemy tłumaczenia (bez tego testy porównujące komunikaty po polsku padają):
```
docker compose -f docker-compose.local.yml run --rm --entrypoint sh mcod-local-tests -c "python manage.py compilemessages --settings mcod.settings.test >/dev/null 2>&1; pytest -m 'not depends_on_component' mcod/harvester/tests mcod/resources/tests mcod/search/tests --no-cov -n0 -p no:cacheprovider -q"
```
Szybszy wariant, tylko to, czego dotykają nasze zmiany: `mcod/harvester/tests/test_schemas.py`, `test_serializers.py`, `test_ckan_partial_imports.py`, `mcod/resources/tests/test_forms.py`, `test_models.py`, `mcod/search/tests`.

Testy komponentu API (około 26 minut na Macu):
```
docker compose -f docker-compose.local.yml run --rm -e COMPONENT=api --entrypoint sh mcod-local-tests-api -c "python manage.py compilemessages --settings mcod.settings.test >/dev/null 2>&1; pytest -m component_api mcod/resources/tests/test_api.py mcod/search/tests mcod/resources/tests/test_views.py --no-cov -n0 -p no:cacheprovider -q"
```
Testy używają osobnej bazy i indeksów z prefiksem `test-`, więc nie ruszają danych demo. U nas wszystkie uruchomione grupy przeszły (harvester, zasoby, wyszukiwarka, API).

### 1.4 Styl (reguły projektu)
Z katalogu `backend/`, w venv z `flake8 black==24.3.0 isort`:
```
.venv/bin/flake8 --config .flake8 --max-line-length 130 mcod/aed
.venv/bin/black --check --line-length 130 mcod/aed
.venv/bin/isort --check-only --multi-line 3 --trailing-comma --line-length 100 --combine-as --profile black mcod/aed
```
Oczekiwane: bez uwag.

## 2. Ręczne scenariusze (end-to-end)
Id zbioru i zasobu zależą od bazy. U nas zbiór zbiorczy ma id 4214, a zasób 40213. Szukaj po tytule „Ogólnopolski wykaz defibrylatorów AED”.

**S1. Dostawca publikuje wykaz.** `docker exec mcod-admin python manage.py aed_seed_demo`, potem `aed_build_main`.
Oczekiwane: 3 instytucje z wykazami, **11 rekordów** w zbiorczym (z 14 wierszy), 3 uwagi w raporcie. Szczegóły: `przykladowe-dane/01-wykazy-dostawcow/README.md`.
Ręcznie: panel, Zasoby, Dodaj, plik z `01-wykazy-dostawcow/`, „Wykaz defibrylatorów AED: Tak”.

**S2. Odrzucenia.** Pliki z `przykladowe-dane/03-pliki-odrzucane/` (oczekiwane komunikaty w README tego folderu): zła kolejność kolumn, zły format, drugi wykaz tej samej instytucji.

**S3. Konwerter.** `https://admin.mcod.local/aed/konwerter/`, pliki z `przykladowe-dane/02-konwerter/`.
Oczekiwane: 3 z 4, 3 z 5 (profil `osm`, data 2026-11-20), 5 z 6, 3 z 3. Pobierz wzorzec przyciskiem na górze strony.

**S4. Efekt w portalu.** Strona zbioru zbiorczego ma 3 zasoby: wykaz (CSV), raport z ostatniego scalenia i wersję GeoJSON.
- Zasób zbiorczy: licencja CC BY 4.0 (sekcja „Warunki wykorzystywania”, Rozwiń), tabela z kolumnami Aktualność, Wiarygodność, Uwagi do danych, zakładka **Mapa** z 11 punktami.
- Id zasobu zbiorczego **nie zmienia się** po kolejnym `aed_build_main` (aktualizacja w miejscu).
- Raport ma wiersze z numerem wiersza w pliku i powodem.

**S5. Zmiany między scaleniami.** Po pierwszym scaleniu uruchom `aed_build_main` drugi raz: w raporcie nie ma wierszy „zmieniony rekord”. Zmień dane dostawcy
(podmień plik zasobu) i scal ponownie: w raporcie pojawiają się wiersze „nowy rekord”, „usunięto z wykazu zbiorczego” lub „zmieniony rekord” z opisem „przed -> po”. (Mechanizm sprawdziliśmy na prawdziwym poprzednim pliku z symulowanymi zmianami, a nie przez edycję pliku w panelu.)

**S6. API.** Filtr wykazów AED (oczekiwane `count: 4`) i punkty mapy:
```
curl -sk --resolve api.mcod.local:443:127.0.0.1 "https://api.mcod.local/1.4/resources?contains_aed_list=true&per_page=1"
curl -sk --resolve api.mcod.local:443:127.0.0.1 "https://api.mcod.local/1.4/resources/40213/geo?per_page=100"
```
Licencja zbioru: `/1.4/datasets/4214` (pole `license_name`: `CC BY 4.0`).

**S7. Import XML i CKAN.** Przykład XML: `przykladowe-dane/04-import-xml/` (README opisuje wymagania). Pełny import wymaga publicznego adresu plików, patrz sekcja 3.

**S8. Telefon i tablet.** Strona konwertera: narzędzia deweloperskie przeglądarki, tryb urządzenia, szerokości 375 i 768 px. Oczekiwane: brak poziomego przewijania strony,
tabele przewijają się w swoich ramkach, menu panelu pod treścią poniżej 768 px.

**S9. Dostępność (szybka kontrola).** Nawigacja samą klawiaturą po stronie konwertera (kolejność Tab, widoczne obramowanie fokusu na przyciskach), czytelność na ciemnym i jasnym tle,
etykiety pól formularza.

## 3. Czego ta instrukcja i nasze testy nie pokrywają
- **Pełnego importu XML 1.14 i CKAN** przez źródło danych w panelu (sprawdziliśmy walidatory zasobu na przykładowych danych i plik XML względem XSD).
- **Pełnego zestawu testów portalu** (m.in. CMS, raporty, użytkownicy). `makemigrations --check` zgłasza migrację w aplikacji `users` (`last_logged_method`), niezwiązaną z naszymi zmianami.
- **Prawdziwego telefonu** i działającego panelu w przeglądarce wbudowanej w narzędzia (certyfikat): responsywność sprawdzona w emulacji na statycznej kopii strony z prawdziwymi stylami panelu.
- **Prawdziwych danych dysponentów** (przykłady są syntetyczne) i geokodowania adresów (konwerter wymaga współrzędnych, patrz „Ograniczenia” w `JURY.md`).
- **Harmonogramu** codziennego scalenia (Celery beat nie jest lokalnie włączony; scalenie uruchamia się komendą).

## 4. Typowe problemy
- **Front pokazuje 502:** nie działa serwer Angulara na porcie 4200 (`npm run start:local` w `frontend/`) albo nginx wskazuje zły adres hosta (patrz `host-gateway` w `docker-compose.yml`).
- **`mcod-rabbitmq` kończy się od razu** (błąd `.erlang.cookie eacces`): usuń wolumen `backend_rabbitmq_vol` i uruchom ponownie.
- **Indeksy Elasticsearch odrzucają ustawienia** (`unknown setting [index.timeout]`): usuń linie `"timeout": 1` z `ELASTICSEARCH_DSL_INDEX_SETTINGS` w `mcod/settings/local.py`.
- **Pliki z komend `docker compose run` nie trafiają do Celery:** zapisujące komendy uruchamiaj przez `docker exec mcod-admin ...`.
- **Zasób zbiorczy ma status błędu danych:** sprawdź komunikat zadania walidacji zasobu. Kolumna liczbowa z pustymi wartościami psuje typ wnioskowany przez portal (dlatego „Pewność połączenia” jest tekstem).
- **Mac zamula:** obrazy są amd64 i działają w emulacji. Zamknij inne programy zajmujące pamięć (np. modele lokalne) i wyłącz zbędne kontenery (`mcod-smtp`, `mcod-api`).

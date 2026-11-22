<a id="readme-top"></a>

[![Django][django-shield]][django-url]
[![Angular][angular-shield]][angular-url]
[![PostgreSQL][postgres-shield]][postgres-url]
[![Elasticsearch][es-shield]][es-url]
[![Docker][docker-shield]][docker-url]
[![CC BY 4.0][ccby-shield]][ccby-url]
[![HackNation][hacknation-shield]][hacknation-url]

# Misja AED: wspólny wykaz defibrylatorów w dane.gov.pl

Rozwiązanie na zadanie konkursowe **Misja AED - Dane na ratunek** (HackNation 2026, Ministerstwo Cyfryzacji).
Nazwa akcji: **„Przez dane do serca”**, hasło: **„Zdążysz, jeśli wiesz gdzie.”**

**Prototyp online: [aed.haloware.pl](https://aed.haloware.pl)**. Instrukcja dla jury: [`JURY.md`](JURY.md).

---

<details>
  <summary>Spis treści</summary>
  <ol>
    <li><a href="#pomysł-w-skrócie">Pomysł w skrócie</a></li>
    <li><a href="#akcja-i-identyfikacja-wizualna">Akcja i identyfikacja wizualna</a></li>
    <li><a href="#co-jest-w-repozytorium">Co jest w repozytorium</a></li>
    <li><a href="#pierwsze-kroki">Pierwsze kroki</a></li>
    <li><a href="#wykorzystanie-sztucznej-inteligencji">Wykorzystanie sztucznej inteligencji</a></li>
    <li><a href="#prawa-autorskie-i-elementy-cudze">Prawa autorskie i elementy cudze</a></li>
    <li><a href="#dane-i-licencje">Dane i licencje</a></li>
  </ol>
</details>

---

## Pomysł w skrócie
Dane o defibrylatorach AED są rozproszone, niepełne i niczyje. Rozszerzamy kod portalu dane.gov.pl o nowy typ zasobu, **wykaz AED**
(wzorowany na istniejącym wykazie DGA): każdy dysponent publikuje własny wykaz w jednolitym układzie kolumn i **sam odpowiada za jego jakość**,
a portal codziennie **scala wykazy wszystkich dostawców w jeden ogólnopolski zbiór** (CSV i GeoJSON, licencja CC BY 4.0)
z kolumnami: dysponent, zakres referencyjny źródła, aktualność, wiarygodność, raport zmian. Do tego konwerter, który zamienia
dowolny plik dysponenta (inne nazwy kolumn, współrzędne w PL-1992, OpenStreetMap) na wzorcowy układ.

**Dla jury zacznij od [`JURY.md`](JURY.md)**: instrukcja krok po kroku, gdzie sprawdzić każde wymaganie z treści zadania.

<p align="right">(<a href="#readme-top">powrót na górę</a>)</p>

---

## Akcja i identyfikacja wizualna
Akcja ma zachęcić dysponentów (urzędy, szkoły, spółdzielnie, centra handlowe, firmy) do udostępnienia lokalizacji AED w portalu dane.gov.pl.
Całość jest w [`identyfikacja-wizualna/`](identyfikacja-wizualna/):
- **Logotyp** w wariantach poziomym, z hasłem i samym znakiem (kolor, negatyw, mono): **JPG, PNG, PDF i SVG** (format otwarty), także wersje na przezroczystym tle.
- **Księga znaku** ([`ksiega-znaku.pdf`](identyfikacja-wizualna/ksiega-znaku.pdf)): opis koncepcji (4 zdania), kolorystyka, konstrukcja i pole ochronne, minimalna wielkość,
  niedozwolone użycia, typografia, wersje znaku, przykłady zastosowań i komunikaty do dysponentów.
- **Materiały promocyjne** (`identyfikacja-wizualna/materialy/`): plakat A3 (PDF do druku i PNG), naklejka „Ten AED jest w bazie” (okrąg 100 mm z kodem QR, SVG, PDF i PNG),
  baner dla dane.gov.pl (1200 × 300 px, także @2x), post kwadratowy do mediów społecznościowych i **animowane logo** (`logo-animowane.svg`: serce, rysująca się linia EKG, uderzenie i napis; pętla 5 s, przy ustawieniu systemu „ogranicz ruch” pokazuje się statyczne logo). Do tego zestaw ikon (favicon, ikony aplikacji) w `ikony/`.
  Materiały pokazują, jak mogłaby wyglądać kampania. Nie są działającymi usługami (np. wspomniane w nich mapa i formularz zgłoszeniowy to przykładowe wezwania do działania).

<p align="right">(<a href="#readme-top">powrót na górę</a>)</p>

---

## Co jest w repozytorium
| Katalog | Zawartość |
|---|---|
| [`JURY.md`](JURY.md) | instrukcja dla jury, algorytmy, ograniczenia |
| `backend/` | kod portalu dane.gov.pl (Django) **wraz z naszym rozszerzeniem w `backend/mcod/aed/`** |
| `frontend/` | front portalu (Angular) |
| `przykladowe-dane/` | **przykładowe dane do importu i testów** z oczekiwanymi wynikami (wykazy dostawców, pliki dla konwertera, pliki odrzucane, import XML) |
| `aed-demo/` | wzorcowy plik xlsx (wymagany w zadaniu) i generator przykładowych danych |
| [`TESTOWANIE.md`](TESTOWANIE.md) | jak testować wszystko: testy automatyczne i ręczne scenariusze |
| `identyfikacja-wizualna/` | logo, ikony, materiały i księga znaku |
| `wymagania-konkursowe/` | treść i regulamin zadania |

Zmiany w istniejącym kodzie portalu są addytywne (patrz `backend/CHANGELOG.md`, sekcja Unreleased), bez nowych zależności.

<p align="right">(<a href="#readme-top">powrót na górę</a>)</p>

---

## Pierwsze kroki
Misję AED można przetestować na dwa sposoby:
- **Online, bez instalacji:** otwórz **[aed.haloware.pl](https://aed.haloware.pl)** i przejdź ścieżkę z [`JURY.md`](JURY.md) (dostawca dodaje wykaz, konwerter, ogólnopolski zbiór).
- **Lokalnie:** uruchom portal na własnym komputerze według instrukcji poniżej.

### Wymagania
- [Docker](https://docs.docker.com/get-docker/) z Docker Compose v2 (kilka GB pamięci; obrazy są amd64, więc na Macu z procesorem ARM działają w emulacji)
- [Node.js](https://nodejs.org) ≥ 20 i npm (tylko dla frontu)
- Opcjonalnie Python 3 (tylko do testów logiki AED bez Dockera)

### Instalacja
Polecenia wykonuj z katalogu `backend/`, jeśli nie napisano inaczej. Pełna instrukcja: [`backend/README.md`](backend/README.md) i [`frontend/README.md`](frontend/README.md).

1. Sklonuj repozytorium
   ```sh
   git clone https://github.com/opietrzko/misja-aed.git
   cd misja-aed/backend
   ```

2. Skopiuj konfigurację
   ```sh
   cp env.sample .env
   cp mcod/settings/local.py.sample mcod/settings/local.py
   ```
   W `.env`: ustaw `DISCOURSE_FORUM_ENABLED=false`, wpisz własny `FIELD_ENCRYPTION_KEYS` (sposób generowania jest w `backend/README.md`) i dopisz zmienne `MCOD_NGINX_*` z tego samego pliku.
   W `local.py`: usuń linie `"timeout": 1` z `ELASTICSEARCH_DSL_INDEX_SETTINGS` (Elasticsearch 6.8 odrzuca to ustawienie).

3. Dopisz nazwy hostów do pliku `hosts` (Linux i macOS: `/etc/hosts`, Windows: `C:\Windows\System32\drivers\etc\hosts`; wymaga uprawnień administratora)
   ```text
   127.0.0.1 mcod.local api.mcod.local admin.mcod.local cms.mcod.local
   ```
   Certyfikat jest samopodpisany, więc przeglądarka ostrzeże.

4. Zbuduj obrazy (jeśli nie były budowane) i uruchom zależności: bazę, Redis, **RabbitMQ**, Elasticsearch i Fuseki
   ```sh
   docker compose -f docker-compose.local.yml build
   docker compose -f docker-compose.local.yml up -d mcod-db mcod-redis mcod-rabbitmq mcod-elasticsearch mcod-rdfdb mcod-smtp
   ```

5. Przygotuj bazę i indeks wyszukiwarki
   ```sh
   docker compose -f docker-compose.local.yml run --rm mcod-local-run python manage.py init_mcod_db
   docker compose -f docker-compose.local.yml run --rm mcod-local-run python manage.py search_index --rebuild -f
   ```
   Przy istniejącej bazie wystarczy `python manage.py migrate` (stosuje m.in. migrację `resources.0076` i `aed.0001`).

6. Uruchom usługi
   ```sh
   docker compose -f docker-compose.local.yml up -d mcod-local-admin mcod-local-api mcod-local-ws mcod-local-celery mcod-nginx
   ```

7. Uruchom front (z katalogu `frontend/`)
   ```sh
   npm install
   npm run start:local
   ```

8. Usługi będą dostępne pod adresami:

   | Usługa | URL |
   |---|---|
   | Panel administracyjny (dostawca, konwerter) | https://admin.mcod.local |
   | Konwerter AED | https://admin.mcod.local/aed/konwerter/ |
   | API | https://api.mcod.local/1.4/ |
   | Front portalu | http://localhost:4200 |

   Konta deweloperskie do panelu (środowisko lokalne, dane testowe z `backend/README.md`, sekcja o panelu administracyjnym):

   | Rola | Login | Hasło |
   |---|---|---|
   | Dostawca danych (pełnomocnik instytucji) | `pelnomocnik@mcod.local` | `User123!` |
   | Administrator | `admin@mcod.local` | `testadmin123!` |

   To konta wyłącznie lokalnego środowiska deweloperskiego, bez prawdziwych danych.

9. Dane przykładowe i scalenie (przez `docker exec`, a nie `run`, bo pliki muszą trafić do wspólnego katalogu `media` z Celery)
   ```sh
   docker exec mcod-admin python manage.py aed_seed_demo
   docker exec mcod-admin python manage.py aed_build_main
   ```
   Powstaje zbiór „Ogólnopolski wykaz defibrylatorów AED - zbiór zbiorczy” (11 rekordów z 14 wierszy wejściowych).

### Testy
Pełna instrukcja testowania: [`TESTOWANIE.md`](TESTOWANIE.md). Testy logiki AED (bez Dockera), z katalogu `backend/`:
```sh
python3 -m venv .venv && .venv/bin/pip install pandas pytest openpyxl pyproj
PYTHONPATH=. .venv/bin/python -m pytest mcod/aed/tests -c /dev/null --confcutdir=mcod/aed/tests --rootdir=. --ignore=mcod/aed/tests/test_remote_check.py -q
```

<p align="right">(<a href="#readme-top">powrót na górę</a>)</p>

---

## Wykorzystanie sztucznej inteligencji
Zgodnie z regulaminem zadania (§2 ust. 7-8) wskazujemy zakres użycia AI:
- **Kod, testy i dokumentacja techniczna:** pisane z pomocą Claude (Claude Code, Anthropic) pod kierunkiem zespołu.
- **Identyfikacja wizualna** (logo, ikony, materiały, księga znaku): wykonana w programie **Affinity**, w którym pomagał Claude (przez MCP), na podstawie poleceń zespołu.
- **Wkład zespołu:** koncepcja akcji i jej nazwa, kierunek graficzny, analiza zadania i wskazówek mentora, decyzje projektowe (m.in. rozszerzenie portalu
  zamiast osobnego serwisu, licencja CC BY 4.0, rezygnacja z geokodowania zewnętrzną usługą ze względu na licencję) oraz weryfikacja wyników.
- **AI w działaniu prototypu:** brak. Konwerter, walidacja, deduplikacja i ocena wiarygodności to jawne, deterministyczne reguły.

<p align="right">(<a href="#readme-top">powrót na górę</a>)</p>

---

## Prawa autorskie i elementy cudze
Rozwiązanie rozszerza otwarty kod portalu dane.gov.pl (zmiany są addytywne, patrz `backend/CHANGELOG.md`); nasz wkład (moduł `backend/mcod/aed/`, dokumentacja, dane przykładowe,
identyfikacja wizualna) jest autorskim rozwiązaniem zespołu. Znak, serce i linię EKG narysowano od zera jako wektory, bez cudzych ikon i klipartów. Jedyny element cudzy w identyfikacji
to krój **Montserrat** na licencji SIL OFL 1.1 (napis w logo zamieniono na krzywe). W razie wygranej prawa majątkowe zostaną przeniesione na Ministra Cyfryzacji na podstawie umowy
z regulaminu zadania (§4).

<p align="right">(<a href="#readme-top">powrót na górę</a>)</p>

---

## Dane i licencje
- Zbiór zbiorczy jest udostępniany na licencji **CC BY 4.0**. Zasady wobec źródeł o innych licencjach (w tym OpenStreetMap, ODbL) opisuje `JURY.md`.
- Dane w `przykladowe-dane/` i `backend/mcod/aed/demo_data/` są **syntetyczne** (fikcyjni dysponenci).

<p align="right">(<a href="#readme-top">powrót na górę</a>)</p>

<!-- MARKDOWN LINKS & BADGES -->
[django-shield]: https://img.shields.io/badge/Django-2.2-092E20?style=for-the-badge&logo=django&logoColor=white
[django-url]: https://www.djangoproject.com
[angular-shield]: https://img.shields.io/badge/Angular-18-DD0031?style=for-the-badge&logo=angular&logoColor=white
[angular-url]: https://angular.dev
[postgres-shield]: https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white
[postgres-url]: https://postgresql.org
[es-shield]: https://img.shields.io/badge/Elasticsearch-6.8-005571?style=for-the-badge&logo=elasticsearch&logoColor=white
[es-url]: https://www.elastic.co/elasticsearch
[docker-shield]: https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white
[docker-url]: https://docker.com
[ccby-shield]: https://img.shields.io/badge/dane-CC%20BY%204.0-EF9421?style=for-the-badge&logo=creativecommons&logoColor=white
[ccby-url]: https://creativecommons.org/licenses/by/4.0/deed.pl
[hacknation-shield]: https://img.shields.io/badge/HackNation-2026-C0392B?style=for-the-badge
[hacknation-url]: https://hacknation.pl

# Misja AED: wspólny wykaz defibrylatorów w dane.gov.pl

Rozwiązanie na zadanie konkursowe **Misja AED - Dane na ratunek** (HackNation 2026, Ministerstwo Cyfryzacji).
Hasło akcji na logo: **„Przez dane do serca”**.

## Pomysł w skrócie
Dane o defibrylatorach AED są rozproszone, niepełne i niczyje. Rozszerzamy kod portalu dane.gov.pl o nowy typ zasobu, **wykaz AED**
(wzorowany na istniejącym wykazie DGA): każdy dysponent publikuje własny wykaz w jednolitym układzie kolumn i **sam odpowiada za jego jakość**,
a portal codziennie **scala wykazy wszystkich dostawców w jeden ogólnopolski zbiór** (CSV i GeoJSON, licencja CC BY 4.0)
z kolumnami: dysponent, zakres referencyjny źródła, aktualność, wiarygodność, raport zmian. Do tego konwerter, który zamienia
dowolny plik dysponenta (inne nazwy kolumn, współrzędne w PL-1992, OpenStreetMap) na wzorcowy układ.

**Dla jury zacznij od [`JURY.md`](JURY.md)**: instrukcja krok po kroku, gdzie sprawdzić każde wymaganie z treści zadania.

## Co jest w repozytorium
| Katalog | Zawartość |
|---|---|
| [`JURY.md`](JURY.md) | instrukcja dla jury, algorytmy, ograniczenia |
| `backend/` | kod portalu dane.gov.pl (Django) **wraz z naszym rozszerzeniem w `backend/mcod/aed/`** |
| `frontend/` | front portalu (Angular) |
| `aed-demo/` | wzorcowy plik xlsx (wymagany w zadaniu) i generator danych demo |
| `identyfikacja-wizualna/` | logo, ikony, materiały i księga znaku |
| `wymagania-konkursowe/` | treść i regulamin zadania |

Zmiany w istniejącym kodzie portalu są addytywne (patrz `backend/CHANGELOG.md`, sekcja Unreleased), bez nowych zależności.

## Skrót uruchomienia lokalnie
Pełna instrukcja: [`backend/README.md`](backend/README.md) i [`frontend/README.md`](frontend/README.md). Rzeczy, o które łatwo się potknąć:
- w `backend/`: skopiuj `env.sample` do `.env` oraz `mcod/settings/local.py.sample` do `mcod/settings/local.py`; wpisz własny `FIELD_ENCRYPTION_KEYS`,
  ustaw `DISCOURSE_FORUM_ENABLED=false` i dopisz zmienne `MCOD_NGINX_*` z `backend/README.md`;
- w `local.py` usuń linie `"timeout": 1` z `ELASTICSEARCH_DSL_INDEX_SETTINGS` (Elasticsearch 6.8 odrzuca to ustawienie);
- `docker compose -f docker-compose.local.yml build`, potem uruchom zależności (baza, Redis, **RabbitMQ**, Elasticsearch), `run --rm mcod-local-run python manage.py init_mcod_db`,
  `search_index --rebuild -f` i usługi `mcod-local-admin`, `mcod-local-api`, `mcod-local-ws`, `mcod-local-celery`, `mcod-nginx`;
- wpis w `/etc/hosts`: `127.0.0.1 mcod.local api.mcod.local admin.mcod.local cms.mcod.local`; certyfikat jest samopodpisany;
- front: `cd frontend && npm install && npm run start:local` (port 4200);
- dane demo i scalenie uruchamiaj przez `docker exec mcod-admin python manage.py aed_seed_demo` i `aed_build_main` (nie przez `run`, bo pliki muszą trafić do wspólnego katalogu `media` z Celery);
- obrazy są amd64, więc na Macu z procesorem ARM działają w emulacji i potrzebują sporo pamięci (kilka GB dla Dockera).

Testy logiki AED (bez Dockera), z katalogu `backend/`:
`python3 -m venv .venv && .venv/bin/pip install pandas pytest openpyxl pyproj`
`PYTHONPATH=. .venv/bin/python -m pytest mcod/aed/tests -c /dev/null --confcutdir=mcod/aed/tests --rootdir=. --ignore=mcod/aed/tests/test_remote_check.py -q`

## Wykorzystanie sztucznej inteligencji
Zgodnie z regulaminem zadania (§2 ust. 7-8) wskazujemy zakres użycia AI:
- **Kod, testy i dokumentacja techniczna:** pisane z pomocą Claude (Claude Code, Anthropic) pod kierunkiem zespołu.
- **Identyfikacja wizualna** (logo, ikony, materiały, księga znaku): wykonana w programie **Affinity**, w którym pomagał Claude (przez MCP), na podstawie poleceń zespołu.
- **Wkład zespołu:** koncepcja akcji i jej nazwa, kierunek graficzny, analiza zadania i wskazówek mentora, decyzje projektowe (m.in. rozszerzenie portalu
  zamiast osobnego serwisu, licencja CC BY 4.0, rezygnacja z geokodowania zewnętrzną usługą ze względu na licencję) oraz weryfikacja wyników.
- **AI w działaniu prototypu:** brak. Konwerter, walidacja, deduplikacja i ocena wiarygodności to jawne, deterministyczne reguły.

## Dane i licencje
- Zbiór zbiorczy jest udostępniany na licencji **CC BY 4.0**. Zasady wobec źródeł o innych licencjach (w tym OpenStreetMap, ODbL) opisuje `JURY.md`.
- Dane w `aed-demo/` i `backend/mcod/aed/demo_data/` są **syntetyczne** (fikcyjni dysponenci).

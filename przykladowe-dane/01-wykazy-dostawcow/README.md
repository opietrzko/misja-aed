# 01 - wykazy dostawców (układ wzorca)

Trzej fikcyjni dysponenci. Pliki csv i xlsx mają tę samą zawartość.

| Plik | Dysponent | Wierszy | Co pokazuje |
|---|---|---|---|
| `urzad-miasta-demo-krakow` | Urząd Miasta Demo-Kraków | 5 | zwykły wykaz; rekord DEMO-UM-001 jest też u Fundacji (duplikat); DEMO-UM-004 ma status „do weryfikacji" |
| `fundacja-demo-ratownik` | Fundacja Demo-Ratownik | 6 | FDR-0001 to to samo urządzenie co DEMO-UM-001; FDR-0005 ma szerokość poza Polską; FDR-0006 ma niedozwolony status |
| `wcr-demo-gdansk` | Wojewódzkie Centrum Ratownictwa Demo-Gdańsk | 3 | czysty wykaz bez błędów |

## Jak użyć
**Szybko (komendy):**
```
docker exec mcod-admin python manage.py aed_seed_demo
docker exec mcod-admin python manage.py aed_build_main
```
`aed_seed_demo` tworzy instytucje, zbiory i zasoby z flagą wykazu AED (pomija te, które już istnieją). `aed_build_main` scala wykazy w zbiorczy.

**Ręcznie:** panel administracyjny, Zasoby, Dodaj, wybierz zbiór instytucji, wgraj plik csv lub xlsx i ustaw „Wykaz defibrylatorów AED: Tak".
Instytucja może mieć tylko jeden wykaz AED.

## Oczekiwany wynik scalenia
- **14 wierszy wejściowych, 11 rekordów** w wykazie zbiorczym (2 odrzucone, 1 duplikat połączony).
- Raport scalania ma **3 uwagi**:

| Dysponent | Wiersz | Identyfikator | Wynik |
|---|---|---|---|
| Fundacja Demo-Ratownik | 6 | FDR-0005 | odrzucono wiersz (współrzędne poza obszarem Polski) |
| Fundacja Demo-Ratownik | 7 | FDR-0006 | odrzucono wiersz (niedozwolona wartość w „Status urządzenia") |
| Urząd Miasta Demo-Kraków | 2 | DEMO-UM-001 | połączono z innym dysponentem (FDR-0001, odległość 4 m, pewność 99%) |

- FDR-0001 ma „Liczba źródeł" 2 i w „Pozostali dysponenci" wpis „Urząd Miasta Demo-Kraków (DEMO-UM-001)".
- Wiersze rozkładają się na trzech dysponentów (Fundacja 4, Urząd 4, WCR 3 po scaleniu).

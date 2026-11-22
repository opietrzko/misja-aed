# 02 - pliki dla konwertera

Strona `/aed/konwerter/` w panelu administracyjnym (przycisk „Pobierz wzorcowy plik" jest na górze strony). Konwerter działa na jawnych regułach, bez AI.
Czego plik nie podaje, tego konwerter nie zgaduje: wartość trzeba wpisać w sekcji „Wartości domyślne", inaczej wiersz jest odrzucany.

| Plik | Ustawienia na stronie | Oczekiwany wynik |
|---|---|---|
| `przyklad-inne-kolumny.csv` | bez profilu, bez wartości domyślnych | **3 z 4** wierszy. Współrzędne w PL-1992 przeliczone do WGS84 (notatka w raporcie). A-20 odrzucony: brak godzin i dostępności oraz „bez daty". Po wpisaniu daty weryfikacji i dostępności „w godzinach" przechodzą **4 z 4** |
| `przyklad-osm-overpass-SYNTETYCZNE.json` | profil `osm`, data stanu danych `2026-11-20` | **3 z 5**. Odrzucone: `osm-node-9000003` (brak godzin i dostępności) i `osm-node-9000004` (poza Polską). Status „do weryfikacji" pochodzi z wartości domyślnej profilu, a dostęp „za zgodą" z tagu `access=customers` |
| `przyklad-polskie-naglowki.xlsx` | bez profilu | **5 z 6**. Rozpoznane kolumny (m.in. „Nr ewid.", „Szer. geogr.", „Godz. dostępności", „Data kontroli"). PL-003 z literówką „caołobowo" daje „całodobowo". PL-004 ma zamienione współrzędne (notatka „zamieniono szerokość z długością") i status „uszkodzony" daje „nieczynny". PL-005 odrzucony (brak daty kontroli) |
| `przyklad-wspolrzedne-w-jednej-kolumnie.csv` | bez profilu (separator `;` wykrywany automatycznie) | **3 z 3**. Współrzędne z jednej kolumny „Punkt" w trzech zapisach (`szer, dł`, `POINT(dł szer)`, `dł; szer`). Miejscowość wyjęta z adresu |

Plik OSM jest **syntetyczny** w formacie Overpass (nie pochodzi z OpenStreetMap). Prawdziwe dane z OSM mają licencję ODbL i nie mieszają się ze zbiorem na CC BY (szczegóły w `../../JURY.md`).

**Komenda zamiast strony** (dla dwóch plików, które leżą też w kontenerze):
```
docker exec mcod-admin python manage.py aed_convert /usr/src/mcod_backend/mcod/aed/demo_data/przyklad-inne-kolumny.csv -o /tmp/wynik.csv
docker exec mcod-admin python manage.py aed_convert /usr/src/mcod_backend/mcod/aed/demo_data/przyklad-osm-overpass-SYNTETYCZNE.json --profile osm --data-zrodla 2026-11-20 -o /tmp/osm.csv
```
Wynik zbiorczy z konwertera wgrywa się potem jako zasób z flagą „Wykaz defibrylatorów AED".

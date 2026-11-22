# Przykładowe dane do importu i testów

**Wszystkie dane są syntetyczne** (fikcyjni dysponenci, zmyślone współrzędne i adresy). Powstają z generatora `aed-demo/generate_demo.py`,
więc README, pliki i testy (`backend/mcod/aed/tests/test_sample_data.py`) pozostają zgodne. Oczekiwane wyniki w README poniżej to faktyczne wyniki
przebiegów kodu, pilnowane testem.

| Folder | Do czego | Gdzie wgrać |
|---|---|---|
| [`01-wykazy-dostawcow/`](01-wykazy-dostawcow/) | 3 wykazy dostawców w układzie wzorca (csv i xlsx), z celowymi błędami | zasób z flagą „Wykaz defibrylatorów AED", potem scalenie |
| [`02-konwerter/`](02-konwerter/) | 4 pliki w innym układzie niż wzorzec | strona `/aed/konwerter/` w panelu administracyjnym |
| [`03-pliki-odrzucane/`](03-pliki-odrzucane/) | pliki, które mają zostać odrzucone, z komunikatami | formularz zasobu albo konwerter |
| [`04-import-xml/`](04-import-xml/) | przykład importu XML w schemacie 1.14 z `containsAedList` | źródło danych typu XML (harvester) |

Wzorcowy zakres danych (plik xlsx wymagany w zadaniu): [`../aed-demo/wzorcowy-zakres-danych-AED.xlsx`](../aed-demo/wzorcowy-zakres-danych-AED.xlsx).

Jak to uruchomić w całości, krok po kroku: [`../TESTOWANIE.md`](../TESTOWANIE.md).

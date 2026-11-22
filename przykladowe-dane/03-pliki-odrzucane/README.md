# 03 - pliki, które mają zostać odrzucone

| Plik | Gdzie wgrać | Oczekiwany wynik |
|---|---|---|
| `zle-kolumny.csv` | zasób z flagą „Wykaz defibrylatorów AED: Tak" | odrzucony: kolumny mają inną kolejność niż wzorzec. Komunikat wymienia oczekiwane nazwy i kolejność |
| `zly-format.txt` | zasób z flagą wykazu AED | odrzucony jako nieobsługiwany format (komunikat „Wykaz AED musi być w formacie csv, xls lub xlsx", o ile portal nie odrzuci go wcześniej własną walidacją formatu; w przeglądarce tego nie sprawdzaliśmy) |
| `tylko-adresy-bez-wspolrzednych.csv` | konwerter (także z wpisanymi wszystkimi wartościami domyślnymi) | **0 z 4**. Powód każdego wiersza: „brak współrzędnych (jest adres)" z wyjaśnieniem, że konwerter nie geokoduje, a dane.gov.pl ma własny geokoder niedostępny lokalnie. Identyfikatory w raporcie: AED-0001 do AED-0004 |
| `wspolrzedne-poza-polska.csv` | zasób z flagą wykazu AED (instytucja bez wykazu) | kolumny są poprawne, więc zasób przechodzi walidację formularza, ale scalanie przyjmuje **1 z 3** wierszy. Raport: wiersze 3 i 4 (`OUT-002`, `OUT-003`) odrzucone, „współrzędne poza obszarem Polski". Po teście usuń zasób, żeby nie zostawić testowego rekordu w wykazie zbiorczym |

`tylko-adresy-bez-wspolrzednych.csv` odtwarza układ prawdziwych wykazów urzędów (sam adres, bez współrzędnych), ale ze zmyślonymi nazwami i miejscowością.

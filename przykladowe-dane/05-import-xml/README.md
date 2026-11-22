# 05 - import przez harvester (XML, schemat 1.14)

`przyklad-harvester-1.14.xml` pokazuje nowy opcjonalny element **`containsAedList`** (zasób jest wykazem AED instytucji).
Plik jest **poprawny względem schematu** `backend/data/harvester/xml_import_otwarte_dane_1_14.xsd`, a ten sam plik z przestrzenią nazw 1.13 jest przez
schemat 1.13 odrzucany (nieznany element). Starsze wersje schematu działają bez zmian.

## Jak użyć
1. Opublikuj plik csv z wykazem (np. z `../01-wykazy-dostawcow/`) pod publicznym adresem, który zwraca nagłówek `Content-Type: text/csv`.
   Hosting plików "raw" (np. GitHub) zwraca `text/plain`, więc walidacja formatu go odrzuci.
2. Wpisz ten adres w elemencie `<url>` w pliku XML (zamiast `https://example.com/wykaz-aed.csv`) i opublikuj XML.
3. W panelu dodaj źródło danych typu XML wskazujące na ten plik, dla instytucji bez innego wykazu AED.

## Co sprawdza import
Plik csv pod `url` (200, format csv/xls/xlsx, wzorcowe kolumny), brak jednoczesnej flagi `containsProtectedData`, co najwyżej jeden wykaz w pliku XML i brak
wykazu AED tej instytucji dodanego inną drogą.

**Czego nie sprawdziliśmy:** pełnego importu przez źródło danych w panelu (wymaga publicznego adresu plików). Walidację XSD i walidatory zasobu sprawdziliśmy osobno.

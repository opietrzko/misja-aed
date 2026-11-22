# Prezentacja - wersja robocza

Prezentacja konkursowa (10 slajdów) do zadania **Misja AED - Dane na ratunek**.

| Plik | Co to jest |
|---|---|
| [`Misja-AED-prezentacja-wersja-robocza.pptx`](Misja-AED-prezentacja-wersja-robocza.pptx) | **PowerPoint z animacjami**: 10 slajdów, notatki prelegenta, animowane GIF-y (scena problemu, logo, linia EKG) i **animacja budowania ostatniego slajdu**. Animacje działają w trybie pokazu slajdów (F5) |
| [`zrodla/`](zrodla/) | Źródła talii (HTML i CSS), wyeksportowane z edytora slajdów |

## Uwagi o pliku PowerPoint
- Każdy slajd to obraz (tło) z naniesionymi animowanymi GIF-ami, więc **tekstu na slajdach nie da się w nim edytować**. Do edycji służy talia w edytorze slajdów, a źródła są w `zrodla/`.
- Zrzuty ekranu wstaw w PowerPoincie jako zwykłe obrazy **na szare pola „ZRZUT 1-12”** (Wstaw, Obraz), przycinając je do rozmiaru pola.
- GIF ze sceną problemu odtwarza się raz, a logo i linia EKG w pętli. W widoku edycji widać tylko pierwszą klatkę.
- **Ostatni slajd buduje się sam** po wejściu na niego: kolejne słowa tytułu (efekt „pojawianie się”), potem linia EKG „wjeżdża” od lewej i pulsuje w pętli, na końcu wchodzą zdanie, hasło i znak. Są to zwykłe animacje PowerPointa (Animacje, Okienko animacji) i można je edytować. Słowa, teksty i znak są na tym slajdzie osobnymi obrazami.
- Plik nie był otwierany w PowerPoincie (powstał poza nim), więc przed oddaniem warto go raz otworzyć i przejść w trybie pokazu.

## Co jest jeszcze do zrobienia
- **Pola „ZRZUT 1-12”** (szare ramki na slajdach 3-8) to miejsca na zrzuty ekranu z działającego prototypu. Opis każdego pola mówi, co wstawić.
- **Animacje** (scena problemu, animowane logo, linia EKG na ostatnim slajdzie) są w pliku PowerPoint. 

## Uwagi o źródłach
- Ikony na slajdach pochodzą z edytora (`<x-icon>`). W pliku PowerPoint są zastąpione prostymi odpowiednikami.
- Obrazy w `zrodla/slides/*.html` mają adresy `/_blob/<id>`, które działają tylko w edytorze. Pliki odpowiadają obrazom z repo:

| Id | Plik w repo |
|---|---|
| `23b9ec78aa1da593757b76ad049bc307` | `identyfikacja-wizualna/logo-poziome-negatyw-przezroczyste.png` |
| `58bc19eae875d3ed2fea18241d32a983` | `identyfikacja-wizualna/logo-znak-kolor-przezroczyste.png` |
| `1e541130c21c1da51a8672204ec0ba21` | `identyfikacja-wizualna/materialy/plakat-A3.png` |
| `c9ae3890be930743b1b6cc6052fb4c15` | `identyfikacja-wizualna/materialy/naklejka-ten-aed-jest-w-bazie.png` |
| `078c675347587b56c1fc523d5996b77a` | `identyfikacja-wizualna/materialy/post-kwadrat.png` |
| `ff4e2a5d640b26d54a917b9f6c1d724f` | `identyfikacja-wizualna/materialy/baner-dane-gov-pl.png` |

Prezentacja powstała z pomocą asystenta AI (Claude). Opis użycia AI jest w [`README.md`](../README.md#wykorzystanie-sztucznej-inteligencji).

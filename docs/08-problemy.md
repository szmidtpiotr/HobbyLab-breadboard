# 08 — Rozwiązywanie problemów

## Kody wyjścia `hlbb render`

| Kod | Co znaczy | Co zrobić |
|---|---|---|
| `0` | Wszystko OK, obrazek można pokazać/budować z niego. | Nic. |
| `1` | Rysunek **nie zgadza się** z opisem (zwarcie, brak połączenia, nóżka wiszącą w powietrzu…). Obrazki i tak powstają, z czerwonym ostrzeżeniem na górze. | Przeczytaj komunikaty w `check.txt` (każdy nazywa konkretną nóżkę i dziurkę), popraw `circuit.py`, uruchom ponownie. Nie pokazuj takiego obrazka jako gotowej instrukcji. |
| `2` | Błąd w samym opisie — zła nazwa dziurki, zły pin, dwa elementy o tym samym oznaczeniu. | Komunikat na `stderr` mówi dokładnie co: patrz tabela niżej. |

## Instalacja i uruchomienie

| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| `hlbb: command not found` po `pip install -e .` | `pip`, którego użyłeś, nie jest tym samym Pythonem, z którego wołasz `hlbb` — często dlatego, że zapomniałeś aktywować wirtualne środowisko. | `source .venv/bin/activate` (albo sprawdź `which python3` i `which pip` — powinny wskazywać tę samą instalację), potem spróbuj ponownie. |
| `hlbb render` kończy się kodem `0`, ale w katalogu wyniku nie ma żadnego pliku `.png` (są tylko `.svg`) | Brak `ImageMagick` (`convert`) i brak `rsvg-convert` — narzędzie po cichu pomija zapis `.png`, bez błędu. | Zainstaluj jedno z nich (rozdział [01](01-instalacja.md)). Jeśli zależy Ci tylko na `montaz.html` — nie jest to potrzebne, SVG jest wbudowane bezpośrednio w ten plik. |
| `ModuleNotFoundError: No module named 'hlbb'` przy uruchamianiu własnego skryptu, który robi `from hlbb import *` | Skrypt jest uruchamiany innym Pythonem niż ten, w którym zrobiłeś `pip install -e .`, albo instalacja się nie powiodła. | `pip show hlbb` powinno pokazać informacje o pakiecie w aktywnym środowisku; jeśli nic nie pokazuje, zainstaluj ponownie. |

## Błędy w opisie układu (kod wyjścia `2`)

Komunikaty są zawsze konkretne — nazywają element i miejsce. Kilka typowych:

| Komunikat (fragment) | Co to znaczy |
|---|---|
| `Nieznana dziurka „…”` | Literówka w nazwie dziurki — poprawne nazwy to `a1`…`j63` (litera rzędu + numer kolumny) albo `T+n`/`T-n`/`B+n`/`B-n` dla szyn. |
| `płytka ma kolumny 1–N` | Podana kolumna wykracza poza wybrany rozmiar płytki (`Board.MINI_170` ma 17 kolumn, `HALF_400` — 30, `FULL_830` — 63). |
| `nie ma szyn zasilania` | Próba użycia `T+`/`B-` na płytce `MINI_170`, która nie ma szyn zasilania. |
| `na szynie nie ma dziurki w kolumnie N` | Trafiłeś w co szóstą kolumnę szyny — tam fizycznie nie ma otworu (tak jak na prawdziwej płytce). |
| `wstawiony dwa razy` | Ten sam element (to samo `Part`, nie tylko to samo oznaczenie) wpięty w `bb.place(...)` więcej niż raz. |
| `nie mieści się na płytce stykowej` | Moduł ma `width=None` w swojej definicji — jego rozstaw rzędów nie jest znany/potwierdzony, więc `hlbb` celowo nie pozwala wpiąć go na płytkę (patrz [rozdział 07](07-jak-to-dziala.md)). Połącz go przewodami/kablami zamiast `bb.place(...)`. |
| `nie ma nóżki „X”` | Taka nazwa pinu nie istnieje w tym elemencie — sprawdź dokładną pisownię w [rozdziale 03](03-format-opisu.md) albo w definicji modułu. |
| `Oznaczenie X użyte dwa razy` | Dwa elementy z tym samym `ref` (np. dwa razy `"R1"`) — oznaczenia muszą być unikalne w całym układzie. |

## Płytka PCB (`hlbb kicad`)

| Objaw | Przyczyna | Rozwiązanie |
|---|---|---|
| `--run potrzebuje zmiennej środowiskowej HLBB_KICAD_HOST` | Nie ustawiłeś, na jaki komputer z KiCadem ma się połączyć — to celowe, narzędzie nie zgaduje hosta. | `export HLBB_KICAD_HOST=user@twoj-komputer` przed uruchomieniem (rozdział [05](05-plytka-pcb.md)). |
| `hlbb kicad` kończy się kodem `1` i komunikatem „Najpierw popraw opis” | `hlbb render` na tym samym opisie też by zgłosił błąd — płytki z niesprawdzonego układu nie powstają. | Uruchom `hlbb render`, popraw błędy, dopiero potem `hlbb kicad`. |
| `brak obudowy DIP o rozstawie …` | Układ scalony (`c.dip(...)`) ma rozstaw rzędów, dla którego nie ma gotowej obudowy przewlekanej w KiCadzie (obsługiwane: 0,3", 0,4", 0,6"). | Podaj własną obudowę: `kicad_symbol=`/`kicad_footprint=` przy tworzeniu elementu. |
| `flow.sh` kończy się błędem na etapie ERC/DRC | Na obecnym etapie zdarza się rzadko (schemat generuje się automatycznie), ale możliwe np. przy nietypowych, ręcznie podanych symbolach KiCada. | Przeczytaj `pcb/out/erc.rpt` / `pcb/out/drc.rpt` — komunikaty KiCada są czytelne i wskazują konkretny element/sieć. |

## Czegoś tu nie ma?

Jeśli trafiłeś na błąd, którego nie ma w tej tabeli — komunikaty `hlbb` prawie zawsze mówią
wprost, co jest nie tak (nazwa elementu, nazwa dziurki, konkretna sieć). Jeśli komunikat
naprawdę nic nie mówi, to warte zgłoszenia jako błąd narzędzia, nie Twojej pomyłki.

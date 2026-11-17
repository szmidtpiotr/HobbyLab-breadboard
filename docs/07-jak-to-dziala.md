# 07 — Jak to działa

Nie jest to konieczne do korzystania z narzędzia — ten rozdział jest dla kogoś, kto chce
poprawić coś w kodzie, dopisać nowy element albo zrozumieć, dlaczego sprawdzenie łapie
akurat to, co łapie.

## Mapa plików

```
circuit.py (Twój opis)
        │
        ▼
  hlbb/model.py        — części, piny, sieci, kable: co ma być z czym połączone
  hlbb/breadboard.py   — nazwy dziurek, gdzie leży który element (geometria płytki)
  hlbb/boards.py       — gotowe definicje modułów (Nano, UNO, D1 mini, …)
        │
        ▼
  hlbb/check.py         — czy to, co naprawdę połączone (z breadboard.py), zgadza się
        │                  z tym, co deklaruje model.py
        ├──────────────────────────────┬─────────────────────┐
        ▼                               ▼                     ▼
  hlbb/render_bb.py            hlbb/render_wiring.py    hlbb/assembly.py
  obrazek płytki stykowej      obrazek połączeń kablami  lista kroków montażu
        │                               │                     │
        └───────────────┬───────────────┴─────────────────────┘
                         ▼
                  hlbb/montaz.py  →  montaz.html
                         │
                  hlbb/kicad.py  →  schemat + płytka PCB (opcjonalnie)
```

`hlbb/svg.py` to wspólne, małe funkcje rysujące (linie, tekst, kolory), używane zarówno
przez `render_bb.py`, jak i `render_wiring.py`. `hlbb/png.py` zamienia `.svg` na `.png` przez
ImageMagick albo `rsvg-convert`, jeśli jeden z nich jest zainstalowany. `hlbb/cli.py` spina
to wszystko w dwa polecenia (`hlbb render`, `hlbb kicad`).

## Dlaczego opis w Pythonie, a nie np. plik YAML albo JSON

Python daje za darmo rzeczy, które w czystym formacie danych trzeba by wymyślać osobno:
pętle (np. żeby wygenerować 8 identycznych kanałów), funkcje pomocnicze, komentarze, a przede
wszystkim — błędy składni widać od razu (Python sam się na nich wywali), zamiast po cichu
akceptować literówkę w nazwie klucza. Opis zostaje krótki (kilkanaście–kilkadziesiąt linii),
bo większość pracy (geometria płytki, numeracja pinów modułów) jest już w bibliotece, a nie
w pliku, który piszesz.

## Dlaczego sprawdzenie istnieje jako osobny krok

Dałoby się narysować obrazek wprost z tego, co napisałeś w `c.net(...)` i `bb.place(...)`,
bez żadnej kontroli — tylko że wtedy literówka w numerze dziurki albo zapomniany przewód
wyszłyby dopiero na stole, przy lutownicy. `hlbb/check.py` liczy *od zera*, co jest naprawdę
połączone (patrząc tylko na to, które dziurki stykają się fizycznie i co z czym łączą
przewody), i porównuje to z tym, co deklarujesz w sieciach. Rozjazd w dowolną stronę — coś
połączone, czego nie deklarowałeś (zwarcie), albo coś zadeklarowane, a nie połączone
(przerwa) — jest błędem. Dzięki temu sprawdzenie łapie też błędy, o których nie pomyślałeś
pisząc opis, nie tylko te, które ktoś z góry przewidział.

## Pułapki, na które już się natknięto

- **Moduł zasłania dziurki między swoimi rzędami nóżek.** Jeśli WeMos D1 mini (albo inny
  moduł z rozstawem rzędów) stoi na płytce, dziurki *pod* jego obudową są fizycznie
  niedostępne — sprawdzenie odrzuci próbę wpięcia tam czegokolwiek.
- **D1 mini nigdy nie mieści się na jednej płytce stykowej z obiema nóżkami dostępnymi** —
  jego rozstaw (9 dziurek) w połączeniu z szerokością obudowy zostawia za mało miejsca po
  obu stronach na typowej płytce 400/830. Dlatego w bibliotece zawsze stoi obok płytki.
- **Górna i dolna szyna zasilania nie są ze sobą połączone** (to prawda fizyczna o płytkach
  stykowych, nie uproszczenie) — jeśli układ korzysta z obu, trzeba je spiąć przewodem.
- **Co szósta kolumna szyny nie ma dziurki** — taka jest budowa prawdziwych płytek stykowych
  (szyny mają przerwy co 5 otworów), `hlbb` to odwzorowuje, więc np. `T+6` nie istnieje.
- **Rozstaw rzędów pinów modułu trzeba zmierzyć albo sprawdzić w bibliotece KiCada** — nie da
  się go zgadnąć z samej liczby pinów. Moduły bez potwierdzonego rozstawu (`width=None` w
  `ModuleDef`) zawsze rysują się obok płytki, nigdy na niej — błędny rozstaw spaliłby
  prawdziwy moduł, więc niepewność jest rozwiązywana na korzyść bezpieczeństwa.

## Dopisywanie nowego modułu

Zobacz `hlbb/boards.py` — każdy wpis to piny w kolejności numeracji (ta sama, co w bibliotece
symboli KiCada: licząc dookoła obudowy, jak w układzie DIP) i rozstaw rzędów w jednostkach
siatki 2,54 mm (`None`, jeśli nieznany albo moduł się nie mieści). Najpewniejsze źródło tych
liczb to biblioteka KiCada (pozycje padów w pliku `.kicad_mod` obudowy) — jeśli moduł jej nie
ma, jedyna wiarygodna droga to pomiar suwmiarką prawdziwej płytki.

Dalej: [08 — Rozwiązywanie problemów](08-problemy.md).

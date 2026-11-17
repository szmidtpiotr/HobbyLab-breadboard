# 02 — Pierwszy układ

Zbudujemy od zera klasyczny układ: Arduino Nano miga diodą LED podłączoną przez rezystor
do pinu D2. Cel nie jest ambitny — ważne jest przejście całej drogi: napisać opis, puścić
go przez `hlbb`, obejrzeć wynik, zobaczyć, jak wygląda błąd, zanim trafi na płytkę.

## Krok 1: części i co z czym połączone

Ten układ to trzy rzeczy: moduł Arduino Nano, rezystor 330 Ω i dioda LED. Rezystor chroni
diodę przed za dużym prądem. Połączenia: pin D2 Nano → rezystor → anoda diody → katoda diody
→ masa (GND) Nano.

Stwórz plik `moj_uklad.py`:

```python
from hlbb import *

c = Circuit("Miganie diodą LED na Nano")
n = c.module("U1", NANO)
r = c.resistor("R1", "330 Ω")
led = c.led("D1", "czerwona")
```

- `Circuit(...)` — tytuł, który pojawi się na obrazku.
- `c.module("U1", NANO)` — gotowa definicja Arduino Nano (piny, rozstaw) jest już w `hlbb`;
  `"U1"` to oznaczenie, jakie zobaczysz na rysunku (tak jak na schemacie elektronicznym).
- `c.resistor(...)` / `c.led(...)` — pierwszy argument to oznaczenie, drugi wartość
  (dla LED to tylko opis koloru, nie wpływa na nic poza podpisem).

## Krok 2: sieci — co jest z czym połączone

```python
c.net("D2", n["D2"], r[1])
c.net("LED_A", r[2], led["A"])
c.net("GND", led["K"], n["GND"])
```

Sieć to po prostu nazwana grupa pinów, które mają być ze sobą połączone — `n["D2"]` czyta pin
`D2` z modułu Nano po nazwie z sitodruku, `r[1]`/`r[2]` to nóżka 1 i 2 rezystora (dla
dwunóżkowych elementów kierunek jest dowolny), `led["A"]`/`led["K"]` to anoda i katoda
(biegunowość diody *ma* znaczenie — stąd osobne nazwy, nie numery).

To jest **jedyne źródło prawdy** o tym, co ma być połączone. Wszystko dalej — rysunek,
sprawdzenie, montaż — liczy się z tych trzech linii.

## Krok 3: gdzie to leży na płytce stykowej

```python
bb = c.breadboard
```

To od razu da błąd — `c.breadboard` jest `None`, bo nie powiedzieliśmy, na jakiej płytce
budujemy. Dopisz `board=...` do `Circuit(...)`:

```python
c = Circuit("Miganie diodą LED na Nano", board=Board.HALF_400)
```

`Board.HALF_400` to płytka na 400 otworów (jest też `MINI_170` i `FULL_830` — rozmiary jak
w sklepie). Teraz rozmieść elementy — `hlbb` numeruje dziurki literą rzędu i numerem kolumny
(`a1`…`j30` na tej płytce):

```python
bb = c.breadboard
bb.place(n, "h1")              # Nano: dziurka pod jego pierwszym pinem
bb.place(r, "j5", "j20")       # rezystor: dziurka pod nóżką 1, potem pod nóżką 2
bb.place(led, "i20", "i22")    # dioda: dziurka pod anodą, potem pod katodą
```

Skąd te konkretne liczby? Z niczego magicznego — po prostu wybrałem wolne kolumny. Każdy
dwunóżkowy element bierze dwie dziurki w **różnych** kolumnach tej samej połowy płytki
(`a`–`e` albo `f`–`j`), bo te pięć otworów w kolumnie jest ze sobą połączonych fabrycznie —
to jest cała zasada płytki stykowej, i to na niej polega reszta.

Teraz przewody — żeby dociągnąć zasilanie i sygnał do modułu, który leży *obok* płytki (Nano
jest za szeroki, żeby obie jego nóżki weszły w tę samą płytkę — to normalne, większość modułów
tak ma):

```python
bb.wire("i5", n["D2"], "orange")    # sygnał z D2 do rezystora
bb.wire("j22", n["GND"], "black")   # masa z diody do Nano
```

Kolory są tylko dla czytelności obrazka — umowa jest taka, że czerwony to plus, czarny to
masa, reszta dowolna. Zwróć uwagę, że przewód do rezystora wchodzi w `i5`, nie w `j5` —
`j5` zajmuje już nóżka rezystora, a w jedną dziurkę można wpiąć tylko jedną rzecz. Chodziło
o to, żeby trafić w **tę samą kolumnę** (5), więc wystarczy inny wolny rząd tej samej połowy
płytki (`i` zamiast `j`) — sprawdzenie w kroku 4 i tak by to wyłapało, gdyby się pomylić.

## Krok 4: render

```bash
hlbb render moj_uklad.py -o wynik
```

Jeśli wszystko się zgadza, zobaczysz linię kończącą się „SPRAWDZENIE: OK” i katalog `wynik/`
z plikami `breadboard.png`, `montaz.html` i kilkoma innymi (pełna lista w
[rozdziale 01](01-instalacja.md)). Otwórz `montaz.html` — to jest gotowa instrukcja montażu,
krok po kroku, z obrazkiem (szczegóły w [rozdziale 04](04-montaz-krok-po-kroku.md)).

## Krok 5: jak wygląda błąd

Usuń na chwilę linię `bb.wire("j22", n["GND"], "black")` i uruchom render ponownie. Zamiast
„OK” zobaczysz:

```
SPRAWDZENIE: 1 błędów — NIE buduj, popraw opis.
  BŁĄD: sieć GND rozdzielona na 2 części, brakuje połączenia: D1.K [i22] | U1.GND [h4]
```

Kod wyjścia programu to teraz `1` (sprawdź poleceniem `echo $?` zaraz po `hlbb render`), a
obrazek i tak powstał — z czerwonym ostrzeżeniem na górze. **To jest sygnał, żeby nie pokazywać
go nikomu jako instrukcji do budowy** — dopiero kod `0` znaczy, że rysunek naprawdę odpowiada
temu, co opisałeś. Przywróć usuniętą linię i uruchom jeszcze raz, żeby wrócić do stanu OK.

## Co dalej

Ten przykład (z drobnymi różnicami w numerach dziurek) leży gotowy jako
`examples/nano_blink.py` — można go otworzyć i porównać. W repo są jeszcze trzy przykłady,
każdy pokazuje coś innego:

- `examples/nano_leds_button.py` — więcej elementów, przewody do szyn zasilania, przycisk.
- `examples/rc_filter.py` — moduł (Arduino UNO) leżący obok małej płytki.
- `examples/xiao_ring_mic.py` — bez płytki stykowej, same moduły połączone kablami.

Pełna lista elementów, płytek i zasad pisania opisu: [rozdział 03 — Format opisu](03-format-opisu.md).

Dalej: [03 — Format opisu](03-format-opisu.md).

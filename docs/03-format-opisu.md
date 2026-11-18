# 03 — Format opisu układu

Ściąga: wszystkie elementy, płytki i zasady pisania `circuit.py`. Przy nowym układzie
wystarczy przeczytać **tylko ten plik** i jeden przykład z `examples/`, napisać opis
(zwykle kilkanaście–kilkadziesiąt linii) i uruchomić `hlbb render`. Nie trzeba (i nie warto)
rysować SVG ręcznie — ten plik pokazuje, jak zrobić to opisem.

## Polecenie

```bash
hlbb render <projekt>/docs/circuit.py -o <projekt>/docs/breadboard   # hlbb w PATH
```

Wynik: `breadboard.svg/.png` (gdy jest płytka stykowa), `breadboard-bare.svg` (ten sam
obrazek bez legendy, ze znacznikami `data-hl` przy każdym elemencie i przewodzie — do
własnej aplikacji, która chciałaby podświetlać bieżący krok), `wiring.svg/.png`, `check.txt`,
`montaz.html` (strona montażu krok po kroku, z powiększaniem obrazka kółkiem/+/−,
przesuwaniem i trybem „śledź krok” — to z niej się buduje) i `assembly.json` (te same
kroki jako dane, format `hlbb-assembly` v1 — do ewentualnej własnej integracji, np.
ze śledzeniem postępu w aplikacji magazynowej).
Kolejność kroków liczy narzędzie; opisy części (paski rezystora, biegunowość) też.
Kod wyjścia: 0 = OK, 1 = sprawdzenie znalazło błędy (obrazki i tak powstają, z czerwonym
ostrzeżeniem), 2 = błąd w samym opisie (zła dziurka, zły pin) — komunikat po polsku na stderr.
**Nie pokazuj obrazka z kodem 1 osobie, która ma z niego budować.** Popraw opis, aż
będzie 0 — dopiero wtedy obrazek jest wiarygodny.

## Szkielet

```python
from hlbb import *

c = Circuit("Tytuł po polsku", board=Board.HALF_400, notes="Linia 1\nLinia 2")
u = c.module("U1", NANO)                      # gotowe: NANO, UNO, D1_MINI, XIAO_ESP32S3, ESP32_S3_DEVKITC
r = c.resistor("R1", "330 Ω")                 # też: cap, cap_electrolytic (+,-), diode (A,K), led (A,K)
ic = c.dip("U2", "NE555", ["GND", "TRIG", "OUT", "RST", "CV", "THR", "DIS", "VCC"])  # width=3 (0,3")
h = c.header("J1", 4, names=["VCC", "GND", "SDA", "SCL"])
f1 = c.fuse("F1", "PTC 50 mA")                # bezpiecznik (polimerowy/szklany), 2 nóżki, bez biegunowości
q1 = c.transistor("Q1", "BC547B")             # TO-92; pins= nazwy nóżek od lewej patrząc na płaską stronę (domyślnie C,B,E)
u5 = c.to92("U5", "DS18B20", ["GND", "DQ", "VDD"])   # inny układ w TO-92 (czujnik, stabilizator 78L05, TL431)
rgb = c.led_rgb("LED2", "5 mm")              # 4 nóżki w rzędzie: R, wspólna (najdłuższa), G, B; common="A" (+) albo "K" (−)
rv = c.pot("RV1", "10 kΩ")                    # potencjometr: piny 1, W (suwak), 3
tvs = c.diode("D1", "P6KE33CA", bidirectional=True, kind_pl="dioda TVS")   # dwukierunkowa = bez paska
br = c.dip("BR1", "DB107", ["~A", "~B", "+", "-"], kind_pl="mostek prostowniczy")  # kind_pl = nazwa w krokach
dht = c.header("U3", 3, value="DHT11", names=["VCC", "DATA", "GND"])  # zastępstwo dla części, której hlbb nie ma
sw = c.button("SW1")                          # piny A1,A2 (zwarte na stałe), B1,B2; wciśnięcie łączy A z B
m = c.module("M1", ModuleDef("BME280", ("VIN", "GND", "SCL", "SDA")))   # własny moduł = lista pinów

c.net("D2", u["D2"], r[1])                    # sieć = co ma być połączone (źródło prawdy)
c.net("GND", u["GND"], ic["GND"], color="black")

bb = c.breadboard                             # tylko gdy board=...
bb.place(u, "h1")                             # moduł/DIP: dziurka pod nóżką 1
bb.place(r, "j5", "j18")                      # 2 nóżki: dziurka nóżki 1, dziurka nóżki 2
bb.place(ic, "f20")
bb.place(h, "a25")                            # listwa: kolejne kolumny w prawo
bb.place(q1, "c12")                           # TO-92/potencjometr: dziurka pod 1. nóżką, reszta w prawo
bb.place(sw, "e27")                           # przycisk okrakiem nad rowkiem, lewa górna nóżka w rzędzie e
bb.wire("j22", "B-22", "black")               # przewód dziurka–dziurka
bb.wire("b25", m["VIN"], "red")               # przewód do modułu leżącego obok płytki
c.cable(u["D4"], m["SDA"], "blue")            # kabel moduł–moduł (bez płytki)
```

## Zasady, które trzeba znać

- **Płytki:** `Board.MINI_170` (17 kolumn, bez szyn), `HALF_400` (30), `FULL_830` (63).
  Szyny: `T+n`, `T-n` (górne), `B+n`, `B-n` (dolne); co 6. kolumna na szynie nie ma dziurki.
  Górne i dolne szyny **nie są** połączone — połącz przewodem, jeśli trzeba.
- **Dziurki:** `a1`…`j63`. Kolumna a–e to jeden pasek, f–j drugi. Rowek między e i f.
  Szyny `T…` leżą nad rzędem a, szyny `B…` pod rzędem j — elementy zasilane z górnej szyny
  kładź w górnej połowie, wtedy przewody są krótkie.
- **Rodzaje elementów:** `resistor`, `cap`, `cap_electrolytic`, `diode`, `led`, `fuse`
  (2 nóżki); `transistor`, `to92`, `pot` (3 nóżki w rzędzie); `led_rgb` (4 w rzędzie); `dip`, `module`, `header`,
  `button`. Każdy przyjmuje `kind_pl="…"` — nazwę w krokach montażu („dioda Zenera”,
  „mostek prostowniczy”). Zastępczy `header` tylko dla rzeczy spoza tej listy, i wtedy
  powiedz osobie budującej, że element jest narysowany jako zwykły blok nóżek.
- **TO-92 (tranzystor, DS18B20, 78L05):** nóżki podajesz w kolejności z karty katalogowej,
  patrząc na płaską stronę z napisem. Na rysunku płaska strona jest u dołu (szary pasek), a w
  krokach montażu: „płaską stroną do siebie”. Zła kolejność nóżek = zły rysunek, więc
  sprawdź kartę katalogową, nie zgaduj (BC547: C,B,E; 2N2222: E,B,C; 2N7000: S,G,D).
- **Nóżka prosto w szynę** jest dozwolona: `bb.place(r, "a15", "T+15")` — oszczędza przewód.
- **Orientacja DIP/modułu:** nóżka 1 w dolnej połowie (f–j) → nóżki idą w prawo, wycięcie
  po lewej. Nóżka 1 w górnej połowie (a–e) → układ obrócony, nóżki idą w lewo.
  Rozstaw rzędów: DIP 3 (e↔f), Nano 6 (c↔g, d↔h), D1 mini 9 (a↔h, b↔i, c↔j).
  XIAO, UNO, DevKitC nie mają rozstawu → zawsze obok płytki (`bb.wire(..., u["pin"])`).
  Moduł zakrywa dziurki między swoimi rzędami nóżek — sprawdzenie odrzuci wpięcie tam.
  **D1 mini na jednej płytce ma zawsze jeden rząd pinów bez wolnej dziurki** — kładź go obok
  płytki. Nano (rzędy d↔h) zostawia wolne a–c i i–j.
- **Nazwy pinów gotowych płytek** (wystarczy dowolna część nazwy po `/`):
  Nano `D0`–`D13`, `A0`–`A7`, `5V`, `3V3`, `GND`, `VIN`, `RST`, `AREF`;
  UNO jak Nano bez A6/A7, plus `IOREF`, `SDA`, `SCL`;
  D1 mini `D0`–`D8`, `A0`, `3V3`, `5V`, `GND`, `RST`, `RX`, `TX` (D5 = `SCK`, D6 = `MISO`, D7 = `MOSI`, D8 = `CS`, D1 = `SCL`, D2 = `SDA`);
  XIAO ESP32-S3 `D0`–`D10`, `3V3`, `5V`, `GND` (też `GPIO1`… i `SDA`/`SCL`/`TX`/`RX`);
  ESP32-S3 DevKitC `GPIO0`–`GPIO48`, `3V3`, `5V`, `GND`, `RST`, `TX`, `RX`.
- **Piny:** po nazwie z sitodruku (`u["D13"]`, `d1["D5"]` = `d1["SCK"]`), po numerze (`u[29]`),
  duplikaty: `u["GND.2"]`. Piny o tej samej nazwie w module są połączone w środku.
- **Bez płytki stykowej** (`board` pominięte): sieci są instrukcją lutowania, sprawdzenie
  pilnuje tylko, żeby pin nie był w dwóch sieciach i kable nie zwierały sieci.
- **Kolory przewodów:** red, black, blue, green, yellow, orange, white, purple, gray, brown,
  pink, cyan. Konwencja: czerwony = plus, czarny = masa.
- **Sprawdzenie łapie:** brakujące połączenie, zwarcie dwóch sieci, połączenie nieopisane
  w sieciach, dwie rzeczy w jednej dziurce, element z obiema nóżkami w jednym pasku,
  nóżkę sieci, która nie jest nigdzie wpięta.

## Gdzie trzymać opis w swoim projekcie

Dowolna konwencja działa — ważne, żeby `circuit.py` i wyniki renderowania leżały obok
siebie i trafiały do commita razem (`<projekt>/docs/circuit.py` +
`<projekt>/docs/breadboard/` to tylko przykład). Jeśli masz już osobną tabelę pin-po-pinie
w innym pliku, niech odsyła do obrazków zamiast je powtarzać — jedno źródło prawdy.


Dalej: [04 — Montaż krok po kroku](04-montaz-krok-po-kroku.md).

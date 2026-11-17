# 06 — Integracja z własną aplikacją (opcjonalnie)

`montaz.html` wystarcza samo w sobie. Ten rozdział jest dla sytuacji, w której masz już
własną aplikację — magazyn części, panel budowy, cokolwiek — i chcesz w niej pokazać ten sam
montaż zamiast (albo obok) gotowej strony `hlbb`. Oba pliki niżej powstają zawsze, bez
dodatkowej flagi.

## `assembly.json` — kroki jako dane

Te same kroki, które widać w `montaz.html`, w formacie do wczytania przez program:

```json
{
  "format": "hlbb-assembly",
  "version": 1,
  "hash": "6f6ea958e03d",
  "title": "Miganie diodą LED: Arduino Nano, pin D2",
  "board": "płytka stykowa 400 pól",
  "notes": "...",
  "ok": true,
  "parts": [
    {"ref": "R1", "kind": "resistor", "kind_pl": "rezystor", "value": "330 Ω",
     "bands": ["pomarańczowy", "pomarańczowy", "brązowy", "złoty"]}
  ],
  "steps": [
    {"id": "s02", "n": 2, "group": "moduly", "title": "U1: moduł Arduino Nano",
     "text": "Wepnij Arduino Nano (U1): nóżka 1 ...", "details": ["..."], "hl": ["p-U1"]}
  ]
}
```

- `hash` — skrót liczony z treści opisu. Jeśli chcesz w swojej aplikacji trzymać postęp
  (które kroki odhaczone) i wgrywać nowe wersje tego samego układu, licz się z tym, że inny
  `hash` = inny układ: albo zeruj postęp, albo dopasowuj kroki po samym tekście (`text`),
  który dla niezmienionego kroku zostaje identyczny między wersjami.
- `ok: false` oznacza, że układ nie przeszedł sprawdzenia — wtedy `steps` jest pustą listą.
  Taki plik warto odrzucić (błąd dla użytkownika), a nie próbować z niego cokolwiek budować.
- `parts` to lista użytych elementów z opisami (łącznie z paskami kolorów rezystora, gdy da
  się je policzyć z wartości) — przydatne, jeśli chcesz dopasować kroki do własnej listy
  części albo magazynu.
- `group` w każdym kroku to jedna z siedmiu wartości, zawsze w tej kolejności: `zbierz`,
  `moduly`, `niskie`, `wysokie`, `przewody`, `kable`, `kontrola`.

## `breadboard-bare.svg` — obrazek do podświetlania

Ten sam rysunek płytki stykowej co w `montaz.html`, ale bez legendy i jako osobny plik —
każdy element i każdy przewód ma atrybut `data-hl="p-R1"` / `data-hl="w-3"` (dopasowany do
`hl` z kroków w `assembly.json`). Jeśli Twoja aplikacja ma własny widok kroków, może
podświetlić bieżący element dopasowaniem CSS po tym atrybucie, np.:

```css
[data-hl="p-R1"] { stroke: red; stroke-width: 3px; }
```

Plik nie ma żadnych skryptów ani stylów całej strony — to czyste, samodzielne SVG, bezpieczne
do wstawienia bezpośrednio w stronę (np. przez `innerHTML` po wczytaniu).

## Dla porównania: nic nie integrować

Jeśli nie masz własnej aplikacji — `montaz.html` jest kompletny sam w sobie i robi dokładnie
to samo (zakładki, podświetlanie, powiększanie, postęp w przeglądarce), bez pisania ani
linijki kodu. Ten rozdział ma sens dopiero, gdy potrzebujesz czegoś więcej (np. wspólny postęp
na kilku urządzeniach przez własny serwer) niż daje pojedynczy plik HTML.

Dalej: [07 — Jak to działa](07-jak-to-dziala.md).

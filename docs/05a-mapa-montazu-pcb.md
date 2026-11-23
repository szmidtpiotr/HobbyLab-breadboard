# 05a — Mapa montażu płytki PCB (opcjonalnie)

Kiedy płytka PCB przyjdzie z fabryki, trzeba na nią przylutować części — często kilkadziesiąt
drobnych elementów SMD. `hlbb mapa` robi z pliku płytki jedną stronę HTML: po lewej lista
części, po prawej obrazek płytki z góry i od spodu.

- **Klik w część na obrazku** oznacza tę jedną sztukę jako przylutowaną (robi się zielona).
  Drugi klik cofa.
- U góry jest licznik „Zostało N z M”.
- Stan pamięta przeglądarka, więc można zamknąć stronę i wrócić później.
- Strona działa bez internetu.

Pod spodem pracuje [InteractiveHtmlBom](https://github.com/openscopeproject/InteractiveHtmlBom);
`hlbb` dokłada do niej klikanie pojedynczych sztuk i polskie opisy części.

## Instalacja InteractiveHtmlBom

Wystarczy wersja bez interfejsu graficznego (bez wxPython):

```bash
python3 -m venv ~/.venvs/ibom
~/.venvs/ibom/bin/pip install --no-deps InteractiveHtmlBom jsonschema
```

Jeśli zainstalujesz ją gdzie indziej, ustaw zmienną `HLBB_IBOM` na ścieżkę do
`generate_interactive_bom`.

## Płytka z EasyEDA (lokalnie)

```bash
hlbb mapa plytka.json --opisy opisy.yml -o out --nazwa moja-plytka
```

Wynik: `out/montaz-moja-plytka.html`.

## Płytka z KiCada (na komputerze z KiCadem)

Pliki `.kicad_pcb` czyta tylko InteractiveHtmlBom uruchomiony obok KiCada 9, więc `hlbb`
kopiuje płytkę przez SSH na Twój komputer z KiCadem i odbiera gotową stronę:

```bash
export HLBB_KICAD_HOST=user@kicad-host
hlbb mapa plytka.kicad_pcb -o out --nazwa top --strony F
```

Na tamtym komputerze InteractiveHtmlBom ma leżeć w
`~/tools/InteractiveHtmlBom` (albo ustaw `HLBB_IBOM_REMOTE` na ścieżkę do
`generate_interactive_bom.py`). `--strony` wybiera widok: `F` góra, `B` spód, `FB` obie.

## Plik `opisy.yml` (opcjonalny, potrzebuje `pip install -e ".[mapa]"`)

```yaml
tytul: Mój odbiornik v1.2
czesci:
  U3:
    opis: Radio 2,4 GHz. Kropka na układzie = nóżka 1. Najpierw pasta, potem gorące powietrze.
  XOLARGE:
    ref: Y1            # nowe oznaczenie wyświetlane na mapie
    wartosc: 52 MHz
dolacz:                # tylko EasyEDA: luźne pady zebrane w jedną część
  U2:
    wartosc: ESP-01F
    obudowa: ESP-01F
    strona: dol
    pady: {ksztalt: RECT, warstwa: 2}   # warstwa: 1 góra, 2 spód, 11 przelotowe
```

Nieznane oznaczenie części w `czesci` to błąd — lepiej dowiedzieć się od razu, że opis
trafił w literówkę, niż szukać go potem na płytce.

Dalej: [06 — Integracja z własną aplikacją](06-integracja.md).

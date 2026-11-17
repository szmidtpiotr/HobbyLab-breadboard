# 01 — Instalacja

## Czego potrzebujesz

- **Python 3.10 lub nowszy.** Sprawdź: `python3 --version`.
- **Do zapisywania obrazków jako `.png`** (opcjonalnie — bez tego dostaniesz tylko `.svg`,
  które też się otwiera w przeglądarce): ImageMagick albo `rsvg-convert`.
  - Linux (Debian/Ubuntu): `sudo apt install imagemagick` albo `sudo apt install librsvg2-bin`
  - macOS: `brew install imagemagick` albo `brew install librsvg`
  - Windows: zainstaluj [ImageMagick](https://imagemagick.org/script/download.php#windows)
    i zaznacz w instalatorze „Add application directory to your system path”.
- **Do strony montażu (`montaz.html`)** nic dodatkowego — to zwykły plik HTML, otwiera się
  w dowolnej przeglądarce, nawet bez internetu.
- **Tylko jeśli chcesz robić płytki PCB** (rozdział [05](05-plytka-pcb.md), opcjonalne):
  osobny komputer z zainstalowanym KiCadem 9 — to osobna instalacja, nie teraz.

## Instalacja

```bash
git clone https://github.com/<ty>/HobbyLab-breadboard
cd HobbyLab-breadboard
pip install -e .
```

`pip install -e .` rejestruje polecenie `hlbb` w Twoim środowisku Pythona (dzięki wpisowi
`[project.scripts]` w `pyproject.toml`) i instaluje samą bibliotekę „na żywo” z tego
katalogu — jeśli później zaktualizujesz repo (`git pull`), zmiany są widoczne od razu,
bez ponownej instalacji.

Jeśli wolisz nie instalować niczego globalnie, zrób to w wirtualnym środowisku:

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .
```

## Sprawdzenie, że działa

```bash
hlbb render examples/nano_blink.py -o /tmp/probny
```

Powinieneś zobaczyć linię kończącą się na „SPRAWDZENIE: OK” i kod wyjścia `0`
(`echo $?` zaraz po poleceniu pokaże `0`). W katalogu `/tmp/probny/` pojawi się kilka
plików — otwórz `montaz.html` w przeglądarce, to jest główny efekt tego narzędzia.

Chcesz się upewnić, że nic się nie zepsuło po własnych zmianach w kodzie? W repozytorium
jest 41 testów automatycznych:

```bash
pip install pytest
python3 -m pytest
```

## Jeśli coś nie działa

Patrz rozdział [08 — Rozwiązywanie problemów](08-problemy.md). Najczęstsze: brak `.png`
mimo że wszystko inne zadziałało (brak ImageMagick/`rsvg-convert` — nieszkodliwe, `.svg`
i `montaz.html` i tak powstają) oraz `hlbb: command not found` (środowisko Pythona, w którym
zrobiłeś `pip install`, nie jest tym samym, z którego wołasz `hlbb` — sprawdź, czy aktywowałeś
`.venv`, jeśli go używasz).

Dalej: [02 — Pierwszy układ](02-pierwszy-uklad.md).

"""Real-browser check of the click add-on (Playwright, headless Chromium)."""
import os

import pytest

from hlbb.cli import main

pw = pytest.importorskip("playwright.sync_api")
HERE = os.path.dirname(__file__)
FIX = os.path.join(HERE, "fixtures", "mapa")
IBOM = os.environ.get("HLBB_IBOM", os.path.expanduser("~/.venvs/ibom/bin/generate_interactive_bom"))

SCREEN_XY = """ref => {
  const i = pcbdata.footprints.findIndex(f => f.ref === ref);
  const fp = pcbdata.footprints[i];
  const L = fp.layer === 'F' ? allcanvas.front : allcanvas.back;
  const t = L.transform, flip = fp.layer === 'B';
  const bb = fp.bbox, a = (bb.angle || 0) * Math.PI / 180;
  const cx = bb.relpos[0] + bb.size[0] / 2, cy = bb.relpos[1] + bb.size[1] / 2;
  const fx = bb.pos[0] + cx * Math.cos(a) - cy * Math.sin(a);
  const fy = bb.pos[1] + cx * Math.sin(a) + cy * Math.cos(a);
  const x = flip ? (-fx * t.s - t.x + t.panx) : (fx * t.s + t.panx + t.x);
  const y = fy * t.s + t.y + t.pany;
  const r = L.highlight.getBoundingClientRect();
  return [r.left + x * t.zoom / devicePixelRatio, r.top + y * t.zoom / devicePixelRatio, i];
}"""


@pytest.fixture(scope="module")
def page_url(tmp_path_factory):
    if not os.path.exists(IBOM):
        pytest.skip("InteractiveHtmlBom not installed")
    if not os.path.exists(os.path.join(FIX, "rx_nano_v1.2_easyeda.json")):
        pytest.skip("no EasyEDA board in tests/fixtures/mapa/")
    out = tmp_path_factory.mktemp("mapa")
    main(["mapa", os.path.join(FIX, "rx_nano_v1.2_easyeda.json"), "--opisy",
          os.path.join(FIX, "rx_nano_opisy.yml"), "-o", str(out), "--nazwa", "rx"])
    return "file://" + str(out / "montaz-rx.html")


def open_page(p, url, errors):
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1400, "height": 900})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(url)
    pg.wait_for_timeout(800)
    return b, pg


def counter(pg):
    return pg.inner_text("#hlbb-licznik")


def test_click_toggles_one_piece_and_persists(page_url):
    errors = []
    with pw.sync_playwright() as p:
        b, pg = open_page(p, page_url, errors)
        assert counter(pg) == "Zostało 18 z 18"
        x, y, i = pg.evaluate(SCREEN_XY, "U3")
        pg.mouse.click(x, y)
        assert counter(pg) == "Zostało 17 z 18"
        assert pg.evaluate("markedFootprints.has(%d)" % i)
        # one piece of a grouped row (C3, C4) -> row checkbox is indeterminate
        x, y, i3 = pg.evaluate(SCREEN_XY, "C3")
        pg.mouse.click(x, y)
        assert counter(pg) == "Zostało 16 z 18"
        assert pg.evaluate("""() => [...document.querySelectorAll('#bombody tr')].some(tr =>
            tr.textContent.includes('C3') && tr.querySelectorAll('input')[1].indeterminate)""")
        pg.reload()
        pg.wait_for_timeout(800)
        assert counter(pg) == "Zostało 16 z 18"
        x, y, _ = pg.evaluate(SCREEN_XY, "U3")
        pg.mouse.click(x, y)                      # second click undoes
        assert counter(pg) == "Zostało 17 z 18"
        # drag across a part does not toggle
        x, y, _ = pg.evaluate(SCREEN_XY, "F1")
        pg.mouse.move(x, y)
        pg.mouse.down()
        pg.mouse.move(x + 60, y + 30, steps=5)
        pg.mouse.up()
        assert counter(pg) == "Zostało 17 z 18"
        b.close()
    assert errors == []

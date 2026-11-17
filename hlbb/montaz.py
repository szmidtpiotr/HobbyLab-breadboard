"""montaz.html: one self-contained page that walks you through the build step by step."""
from __future__ import annotations

import json
from html import escape

CSS = r"""
*{box-sizing:border-box}
body{margin:0;font-family:"DejaVu Sans",system-ui,sans-serif;background:#eef0f3;color:#1b1f27}
header{display:flex;align-items:center;gap:18px;padding:12px 22px;background:#1d2330;color:#fff;flex-wrap:wrap}
header h1{font-size:20px;margin:0;font-weight:700}
header .sub{color:#aab3c5;font-size:14px}
.bar{flex:1;min-width:160px;height:10px;background:#3a4357;border-radius:6px;overflow:hidden}
.bar i{display:block;height:100%;background:#4cc38a;width:0;transition:width .3s}
.count{font-size:15px;white-space:nowrap}
header button,.tabs button{background:#30394c;color:#fff;border:0;border-radius:8px;padding:8px 12px;font-size:14px;cursor:pointer}
header button:hover,.tabs button:hover{background:#3d4861}
main{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(360px,1fr);gap:18px;padding:18px 22px}
.pic{background:#fff;border-radius:14px;padding:10px;box-shadow:0 1px 4px #0002}
.tabs{display:flex;gap:8px;margin-bottom:8px}
.tabs button{background:#dfe3ea;color:#1b1f27}
.tabs button.on{background:#1d2330;color:#fff}
.pic svg{width:100%;height:auto;display:block}
.view{position:relative}
.zoom{overflow:hidden;border-radius:8px;cursor:grab;touch-action:none;user-select:none;height:calc(100vh - 190px);min-height:320px}
.zoom svg{width:100%;height:100%}
.zoom.drag{cursor:grabbing}
.zctl{position:absolute;right:8px;bottom:8px;display:flex;gap:6px;z-index:2}
.zctl button{background:#1d2330e6;color:#fff;border:0;border-radius:8px;min-width:38px;height:36px;font-size:17px;cursor:pointer;padding:0 10px}
.zctl button.on{background:#e08a00}
.zctl button:hover{filter:brightness(1.2)}
.view{display:none}.view.on{display:block}
#bb [data-hl]{transition:opacity .25s}
#bb.focus [data-hl]{opacity:.13}
#bb.focus [data-hl].done{opacity:1}
#bb.focus [data-hl].now{opacity:1;animation:pulse 1.4s ease-in-out infinite}
@keyframes pulse{0%,100%{filter:drop-shadow(0 0 0 #ffbf00)}50%{filter:drop-shadow(0 0 7px #ff9d00) drop-shadow(0 0 3px #ff9d00)}}
aside{display:flex;flex-direction:column;gap:14px;min-width:0}
.card{background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 1px 4px #0002}
.grp{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#6b7487}
.card h2{font-size:22px;margin:6px 0 10px}
.card .txt{font-size:19px;line-height:1.45}
.card ul{margin:10px 0 0;padding-left:20px;font-size:16px;line-height:1.5;color:#363c48}
.bands{display:flex;gap:6px;margin-top:10px}
.bands span{width:34px;height:26px;border-radius:5px;border:1px solid #0004}
.btns{display:flex;gap:10px;margin-top:18px}
.btns button{font-size:17px;padding:12px 16px;border-radius:10px;border:0;cursor:pointer;background:#dfe3ea}
.btns .ok{flex:1;background:#2f9e66;color:#fff;font-weight:700}
.btns .ok.undo{background:#8a93a5}
.btns button:hover{filter:brightness(1.07)}
.hint{font-size:13px;color:#7a8396;margin-top:8px}
.list{position:relative;background:#fff;border-radius:14px;padding:8px 0;box-shadow:0 1px 4px #0002;max-height:52vh;overflow:auto}
.list h3{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#6b7487;margin:10px 18px 4px}
.list div{display:flex;gap:10px;align-items:flex-start;padding:7px 18px;cursor:pointer;font-size:15px}
.list div:hover{background:#f2f4f7}
.list div.now{background:#fff4d6}
.list div b{min-width:26px;color:#6b7487;font-weight:400}
.list input{margin-top:3px;width:17px;height:17px}
.list div.done span{color:#7a8396;text-decoration:line-through}
.err{margin:22px;padding:20px;border-radius:12px;background:#ffe3e3;color:#7a0000;font-size:17px;white-space:pre-wrap}
.fin{background:#d9f5e6;color:#145c38;font-weight:700;padding:12px 16px;border-radius:10px;margin-top:12px;display:none}
@media (max-width:900px){.zoom{height:55vh;min-height:260px}main{grid-template-columns:1fr;padding:10px}.list{max-height:none}header{padding:10px}}
"""

JS = r"""
const D = JSON.parse(document.getElementById('data').textContent);
const KEY = 'hlbb-montaz-' + D.hash;
const BAND = {'czarny':'#111','brązowy':'#7b4a1e','czerwony':'#d22','pomarańczowy':'#f08000','żółty':'#f3d300',
  'zielony':'#1e9e3a','niebieski':'#1f5fd6','fioletowy':'#8a3fc7','szary':'#8c8c8c','biały':'#fff',
  'złoty':'#c9a227','srebrny':'#c0c0c0'};
const GROUPS = {zbierz:'Przygotowanie',moduly:'Moduły i układy scalone',niskie:'Elementy niskie',
  wysokie:'Elementy wyższe',przewody:'Przewody na płytce',kable:'Przewody do modułów',kontrola:'Kontrola'};
let st = {done: [], cur: 0};
try { const s = JSON.parse(localStorage.getItem(KEY)); if (s && Array.isArray(s.done)) st = s; } catch (e) {}
const save = () => localStorage.setItem(KEY, JSON.stringify(st));
const $ = s => document.querySelector(s);
const bb = $('#bb');
const isDone = id => st.done.includes(id);

function paint() {
  const steps = D.steps, step = steps[st.cur];
  const n = st.done.length;
  $('.bar i').style.width = (100 * n / steps.length) + '%';
  $('.count').textContent = `zrobione ${n} z ${steps.length}`;
  // picture: done parts normal, current pulsing, the rest dimmed
  if (bb) {
    const doneHl = new Set(steps.filter(s => isDone(s.id)).flatMap(s => s.hl));
    const nowHl = new Set(step.hl);
    bb.classList.toggle('focus', nowHl.size > 0 || doneHl.size > 0);
    bb.querySelectorAll('[data-hl]').forEach(g => {
      const k = g.dataset.hl;
      g.classList.toggle('now', nowHl.has(k));
      g.classList.toggle('done', doneHl.has(k) && !nowHl.has(k));
    });
    if (!nowHl.size && step.group !== 'zbierz') bb.classList.remove('focus');
  }
  // card
  $('.grp').textContent = GROUPS[step.group] || step.group;
  $('.card h2').textContent = `${step.n}. ${step.title}`;
  $('.card .txt').textContent = step.text;
  $('.card ul').innerHTML = step.details.map(d => `<li>${esc(d)}</li>`).join('');
  const part = D.parts.find(p => step.hl.includes('p-' + p.ref));
  $('.bands').innerHTML = part && part.bands ?
    part.bands.map(b => `<span title="${b}" style="background:${BAND[b]}"></span>`).join('') : '';
  const ok = $('.btns .ok');
  ok.textContent = isDone(step.id) ? 'Cofnij odhaczenie' : 'Zrobione ✓';
  ok.classList.toggle('undo', isDone(step.id));
  $('.fin').style.display = n === steps.length ? 'block' : 'none';
  // list
  document.querySelectorAll('.list div').forEach((el, i) => {
    el.classList.toggle('now', i === st.cur);
    el.classList.toggle('done', isDone(steps[i].id));
    el.querySelector('input').checked = isDone(steps[i].id);
  });
  followStep();
  // keep the current row visible inside the list only (never scroll the whole page,
  // on a phone that would push the picture off screen)
  const list = $('.list'), nowEl = document.querySelectorAll('.list div')[st.cur];
  if (nowEl && list.scrollHeight > list.clientHeight) {
    const top = nowEl.offsetTop;
    if (top < list.scrollTop || top + nowEl.offsetHeight > list.scrollTop + list.clientHeight)
      list.scrollTop = top - list.clientHeight / 3;
  }
}
function esc(s) { return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function go(i) { st.cur = Math.max(0, Math.min(D.steps.length - 1, i)); save(); paint(); }
function toggle(i) {
  const id = D.steps[i].id;
  st.done = isDone(id) ? st.done.filter(x => x !== id) : st.done.concat(id);
  save();
}
function doneAndNext() {
  const was = isDone(D.steps[st.cur].id);
  toggle(st.cur);
  if (!was) {
    const next = D.steps.findIndex((s, i) => i > st.cur && !isDone(s.id));
    if (next >= 0) st.cur = next;
  }
  save(); paint();
}
// ---- zoom & pan on the pictures (viewBox based, text stays sharp) ----
const zooms = {};
function zoomable(view) {
  const box = view.querySelector('.zoom'), svg = box.querySelector('svg');
  // the frame has a fixed size; widen the picture's box to the frame's proportions
  const b0 = svg.viewBox.baseVal, pic = {x: b0.x, y: b0.y, w: b0.width, h: b0.height};
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  const ar = Math.max(0.3, box.clientWidth / Math.max(1, box.clientHeight));
  const v0 = pic.w / pic.h > ar
    ? {x: pic.x, y: pic.y + pic.h / 2 - pic.w / ar / 2, w: pic.w, h: pic.w / ar}
    : {x: pic.x + pic.w / 2 - pic.h * ar / 2, y: pic.y, w: pic.h * ar, h: pic.h};
  const z = {v: {...v0}, v0, follow: false};
  const apply = () => svg.setAttribute('viewBox', `${z.v.x} ${z.v.y} ${z.v.w} ${z.v.h}`);
  const clamp = () => {
    z.v.w = Math.min(v0.w, Math.max(v0.w / 10, z.v.w)); z.v.h = z.v.w * v0.h / v0.w;
    z.v.x = Math.min(v0.x + v0.w - z.v.w, Math.max(v0.x, z.v.x));
    z.v.y = Math.min(v0.y + v0.h - z.v.h, Math.max(v0.y, z.v.y));
  };
  const toSvg = (cx, cy) => { const r = svg.getBoundingClientRect();
    return [z.v.x + (cx - r.left) / r.width * z.v.w, z.v.y + (cy - r.top) / r.height * z.v.h]; };
  z.zoomAt = (f, px, py) => {
    const nw = Math.min(v0.w, Math.max(v0.w / 10, z.v.w * f)), k = nw / z.v.w;
    z.v.x = px - (px - z.v.x) * k; z.v.y = py - (py - z.v.y) * k; z.v.w = nw; clamp(); apply();
  };
  z.center = () => [z.v.x + z.v.w / 2, z.v.y + z.v.h / 2];
  z.fit = () => { z.v = {...v0}; apply(); };
  z.fit();
  z.show = (els, scale) => {             // zoom onto elements, keep their whole extent visible
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    els.forEach(e => { const b = e.getBBox(); if (!b.width && !b.height) return;
      x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height); });
    if (x0 > x1) return false;
    // show the whole board height (row letters, rails, column numbers) around the step
    const pad = 60, w = Math.max((x1 - x0) + 2 * pad, (y1 - y0 + 2 * pad) * v0.w / v0.h,
                                 pic.h * v0.w / v0.h, v0.w / (scale || 3));
    z.v.w = Math.min(v0.w, w); z.v.h = z.v.w * v0.h / v0.w;
    z.v.x = (x0 + x1) / 2 - z.v.w / 2;
    z.v.y = z.v.h >= pic.h ? pic.y + pic.h / 2 - z.v.h / 2 : (y0 + y1) / 2 - z.v.h / 2;
    clamp(); apply(); return true;
  };
  box.addEventListener('wheel', e => { e.preventDefault();
    const [px, py] = toSvg(e.clientX, e.clientY); z.zoomAt(e.deltaY < 0 ? 0.8 : 1.25, px, py); }, {passive: false});
  const pts = new Map(); let last = null, pinch = null;
  box.addEventListener('pointerdown', e => { box.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]);
    box.classList.add('drag'); last = [e.clientX, e.clientY];
    if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = Math.hypot(a[0] - b[0], a[1] - b[1]); } });
  box.addEventListener('pointermove', e => { if (!pts.has(e.pointerId)) return;
    pts.set(e.pointerId, [e.clientX, e.clientY]);
    const r = svg.getBoundingClientRect();
    if (pts.size === 2 && pinch) { const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      const [px, py] = toSvg((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); z.zoomAt(pinch / d, px, py); pinch = d; return; }
    z.v.x -= (e.clientX - last[0]) / r.width * z.v.w; z.v.y -= (e.clientY - last[1]) / r.height * z.v.h;
    last = [e.clientX, e.clientY]; clamp(); apply(); });
  const up = e => { pts.delete(e.pointerId); pinch = null; if (!pts.size) box.classList.remove('drag');
    else last = [...pts.values()][0]; };
  box.addEventListener('pointerup', up); box.addEventListener('pointercancel', up);
  box.addEventListener('dblclick', e => { const [px, py] = toSvg(e.clientX, e.clientY); z.zoomAt(0.5, px, py); });
  const c = view.querySelector('.zctl');
  c.querySelector('.zin').onclick = () => z.zoomAt(0.7, ...z.center());
  c.querySelector('.zout').onclick = () => z.zoomAt(1.4, ...z.center());
  c.querySelector('.zfit').onclick = () => { setFollow(false); z.fit(); };
  const fb = c.querySelector('.zfol');
  const setFollow = on => { z.follow = on; if (fb) fb.classList.toggle('on', on); if (on) followStep(); };
  if (fb) fb.onclick = () => setFollow(!z.follow);
  z.setFollow = setFollow;
  zooms[view.id] = z;
}
function followStep() {
  const z = zooms.bb; if (!z || !z.follow || !bb) return;
  const els = [...bb.querySelectorAll('[data-hl].now')];
  if (!els.length || !z.show(els, 3)) z.fit();
}

function build() {
  let html = '', g = null;
  D.steps.forEach((s, i) => {
    if (s.group !== g) { g = s.group; html += `<h3>${GROUPS[g] || g}</h3>`; }
    html += `<div data-i="${i}"><input type="checkbox" tabindex="-1"><b>${s.n}.</b><span>${esc(s.title)}</span></div>`;
  });
  $('.list').innerHTML = html;
  $('.list').addEventListener('click', e => {
    const row = e.target.closest('div[data-i]'); if (!row) return;
    const i = +row.dataset.i;
    if (e.target.tagName === 'INPUT') { toggle(i); paint(); } else go(i);
  });
  $('.btns .ok').onclick = doneAndNext;
  $('.btns .prev').onclick = () => go(st.cur - 1);
  $('.btns .next').onclick = () => go(st.cur + 1);
  $('#reset').onclick = () => { if (confirm('Wyczyścić wszystkie odhaczenia?')) { st = {done: [], cur: 0}; save(); paint(); } };
  document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => {
    document.querySelectorAll('.tabs button').forEach(x => x.classList.toggle('on', x === b));
    document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === b.dataset.v));
  });
  document.querySelectorAll('.view').forEach(zoomable);
  // big boards start in "follow the step" mode, small ones show the whole picture
  if (zooms.bb && D.board && !/170/.test(D.board)) zooms.bb.setFollow(true);
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') return;
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); doneAndNext(); }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); go(st.cur + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); go(st.cur - 1); }
    else if (e.key === '+' || e.key === '=') { const z = zooms[document.querySelector('.view.on').id]; z.zoomAt(0.7, ...z.center()); }
    else if (e.key === '-') { const z = zooms[document.querySelector('.view.on').id]; z.zoomAt(1.4, ...z.center()); }
    else if (e.key === '0') { const z = zooms[document.querySelector('.view.on').id]; z.setFollow && z.setFollow(false); z.fit(); }
    else if (e.key === 'f' || e.key === 'F') { zooms.bb && zooms.bb.setFollow(!zooms.bb.follow); }
  });
  paint();
}
if (D.steps.length) build();
"""


def _ctl(follow: bool) -> str:
    f = '<button class="zfol" title="Śledź bieżący krok (F)">🔍 krok</button>' if follow else ""
    return (f'<div class="zctl">{f}<button class="zin" title="Powiększ (+)">+</button>'
            f'<button class="zout" title="Pomniejsz (−)">−</button>'
            f'<button class="zfit" title="Cały obrazek (0)">⤢</button></div>')


def render_montaz(assembly: dict, bb_svg: str | None, wiring_svg: str, report: str) -> str:
    data = json.dumps(assembly, ensure_ascii=False).replace("</", "<\\/")
    title = escape(assembly["title"])
    sub = escape(assembly["board"] or "moduły połączone kablami")
    if not assembly["ok"]:
        body = (f'<div class="err"><b>Ten układ nie przeszedł sprawdzenia — nie buduj go.</b>\n\n'
                f'{escape(report)}</div>')
        steps_ui = ""
    else:
        tabs = []
        views = []
        if bb_svg:
            tabs.append('<button class="on" data-v="bb">Płytka</button>')
            views.append(f'<div class="view on" id="bb">{_ctl(True)}<div class="zoom">{bb_svg}</div></div>')
        tabs.append(f'<button{"" if bb_svg else " class=on"} data-v="wr">Połączenia</button>')
        views.append(f'<div class="view{"" if bb_svg else " on"}" id="wr">{_ctl(False)}'
                     f'<div class="zoom">{wiring_svg}</div></div>')
        body = f"""<main>
<section class="pic"><div class="tabs">{''.join(tabs)}</div>{''.join(views)}</section>
<aside>
 <div class="card"><div class="grp"></div><h2></h2><div class="txt"></div><div class="bands"></div><ul></ul>
  <div class="btns"><button class="prev">←</button><button class="ok">Zrobione ✓</button><button class="next">→</button></div>
  <div class="hint">Spacja albo Enter = zrobione, strzałki = poprzedni / następny krok.
   Obrazek: kółko myszy albo + / − = powiększ, przeciągnij = przesuń, F = śledź krok, 0 = cały.</div>
  <div class="fin">Wszystkie kroki odhaczone. Zasilanie dopiero po kontroli.</div>
 </div>
 <div class="list"></div>
</aside></main>"""
        steps_ui = (f'<div class="bar"><i></i></div><span class="count"></span>'
                    f'<button id="reset" title="Wyczyść odhaczenia">Od nowa</button>')
    return f"""<!doctype html>
<html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Montaż: {title}</title><style>{CSS}</style></head>
<body>
<header><div><h1>Montaż: {title}</h1><div class="sub">{sub} · wersja układu {assembly["hash"]}</div></div>
{steps_ui}</header>
{body}
<script type="application/json" id="data">{data}</script>
<script>{JS}</script>
</body></html>
"""

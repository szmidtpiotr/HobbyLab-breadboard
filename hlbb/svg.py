"""Tiny SVG helpers shared by both renderers."""
from __future__ import annotations

from xml.sax.saxutils import escape

COLORS = {
    "red": "#d62728", "black": "#222222", "blue": "#1f63c6", "green": "#1e8c3a",
    "yellow": "#e3b800", "orange": "#e67e00", "white": "#bbbbbb", "purple": "#8e44ad",
    "gray": "#7f7f7f", "grey": "#7f7f7f", "brown": "#8b5a2b", "pink": "#e75480",
    "cyan": "#0aa5b8",
}
COLOR_PL = {
    "red": "czerwony", "black": "czarny", "blue": "niebieski", "green": "zielony",
    "yellow": "żółty", "orange": "pomarańczowy", "white": "biały", "purple": "fioletowy",
    "gray": "szary", "grey": "szary", "brown": "brązowy", "pink": "różowy", "cyan": "turkusowy",
}
NET_PALETTE = ["#1f63c6", "#1e8c3a", "#8e44ad", "#0aa5b8", "#8b5a2b", "#e75480",
               "#7f7f00", "#5b6bd6", "#c0392b"]


def color(c: str | None, default="#1f63c6") -> str:
    if not c:
        return default
    return COLORS.get(c, c)


def color_pl(c: str) -> str:
    return COLOR_PL.get(c, c)


def net_color(name: str, explicit: str | None, idx: int) -> str:
    if explicit:
        return color(explicit)
    u = name.upper()
    if u in ("GND", "MASA", "0V") or u.startswith("GND"):
        return COLORS["black"]
    if u in ("3V3", "+3V3", "3.3V", "VDD"):
        return "#ef6c00"
    if u in ("VCC", "5V", "+5V", "VIN", "VBUS", "12V", "+12V") or u.startswith("V+"):
        return COLORS["red"]
    return NET_PALETTE[idx % len(NET_PALETTE)]


class Svg:
    def __init__(self):
        self.items: list[str] = []

    def add(self, s: str):
        self.items.append(s)

    def text(self, x, y, s, size=14, anchor="start", weight="normal", fill="#222", extra=""):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" fill="{fill}" {extra}>{escape(str(s))}</text>')

    def rect(self, x, y, w, h, fill="none", stroke="none", rx=0, sw=1, extra=""):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

    def line(self, x1, y1, x2, y2, stroke="#222", sw=2, extra=""):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{stroke}" stroke-width="{sw}" {extra}/>')

    def circle(self, x, y, r, fill="none", stroke="none", sw=1):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="{sw}"/>')

    def path(self, d, stroke="#222", sw=3, fill="none", extra=""):
        self.add(f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}" '
                 f'stroke-linecap="round" {extra}/>')

    def render(self, w, h, top=0) -> str:
        """top > 0 crops the drawing from above (used for the bare board view)."""
        body = "\n".join(self.items)
        hh = h - top
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{hh:.0f}" '
                f'viewBox="0 {top:.0f} {w:.0f} {hh:.0f}" font-family="DejaVu Sans, sans-serif">\n'
                f'<rect y="{top:.0f}" width="{w:.0f}" height="{hh:.0f}" fill="white"/>\n{body}\n</svg>\n')


def text_width(s: str, size: float) -> float:
    """Rough width estimate for DejaVu Sans."""
    return len(str(s)) * size * 0.6

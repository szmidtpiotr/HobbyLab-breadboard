"""SVG -> PNG through ImageMagick (install: apt install imagemagick)."""
import shutil
import subprocess


def to_png(svg_path: str, png_path: str) -> bool:
    exe = shutil.which("rsvg-convert")
    if exe:
        cmd = [exe, "-b", "white", "-o", png_path, svg_path]
    else:
        exe = shutil.which("convert") or shutil.which("magick")
        if not exe:
            return False
        cmd = [exe, "-background", "white", "-flatten", svg_path, png_path]
    subprocess.run(cmd, check=True, capture_output=True)
    return True

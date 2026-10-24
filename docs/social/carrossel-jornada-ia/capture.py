"""Renderiza os PNGs do carrossel a partir dos HTMLs em slides/.

Uso (a partir desta pasta):

    python capture.py

Requisitos: `playwright` Python instalado e Chromium
(`python -m playwright install chromium`).

Saída: png/slide-NN.png em 2160x2700 (1080x1350 @2x — nítido no
reescalamento do Instagram), mesma abordagem do
frontend/scripts/site/capture_mock.py (SCALE=2).
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SLIDES = sorted((ROOT / "slides").glob("slide-*.html"))
OUT = ROOT / "png"
W, H, SCALE = 1080, 1350, 2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={"width": W, "height": H}, device_scale_factor=SCALE
    )
    for html in SLIDES:
        page.goto(html.as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        out = OUT / f"{html.stem}.png"
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": W, "height": H})
        print(f"ok {out.name}")
    browser.close()

print(f"{len(SLIDES)} slides -> {OUT}")

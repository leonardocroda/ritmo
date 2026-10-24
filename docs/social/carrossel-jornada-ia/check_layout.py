"""QA de layout dos slides: overflow, fonte e footer dentro do viewport.

Uso: python check_layout.py
Falha (exit 1) se qualquer slide estourar 1080x1350, se a fonte
Instrument Sans não carregar ou se o rodapé sair da tela.
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SLIDES = sorted((ROOT / "slides").glob("slide-*.html"))
W, H = 1080, 1350

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

problems: list[str] = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": W, "height": H})
    for html in SLIDES:
        page.goto(html.as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        m = page.evaluate(
            """() => {
                const de = document.documentElement;
                const footer = document.querySelector('.footer');
                const fr = footer ? footer.getBoundingClientRect() : null;
                return {
                    sw: de.scrollWidth, sh: de.scrollHeight,
                    font: document.fonts.check("700 40px 'Instrument Sans'"),
                    footerBottom: fr ? Math.round(fr.bottom) : null,
                };
            }"""
        )
        name = html.stem
        issues = []
        if m["sw"] > W:
            issues.append(f"overflow horizontal {m['sw']}px")
        if m["sh"] > H:
            issues.append(f"overflow vertical {m['sh']}px")
        if not m["font"]:
            issues.append("fonte Instrument Sans não carregou")
        if m["footerBottom"] is None:
            issues.append("sem .footer")
        elif m["footerBottom"] > H:
            issues.append(f"footer fora do viewport ({m['footerBottom']}px)")
        if issues:
            problems.append(f"{name}: " + "; ".join(issues))
            print(f"FAIL {name}: {'; '.join(issues)}")
        else:
            print(
                f"ok   {name}  (scroll {m['sw']}x{m['sh']}, "
                f"footer@{m['footerBottom']}, fonte ok)"
            )
    browser.close()

if problems:
    sys.exit(1)
print("todos os slides ok")

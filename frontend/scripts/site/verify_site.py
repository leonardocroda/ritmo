"""QA rápido do site público — RODA SEM SESSÃO (visitante).

Verifica as três coisas que o site promete:

1. `/` renderiza a landing para quem não tem sessão (o proxy não
   manda para /login).
2. `/treinos` redireciona o visitante para /login?next=/treinos.
3. O layout segura em 390px (mobile da identidade) e 1440px — prints
   full-page para inspeção visual (saem em temp, não em public/).

Uso: `python scripts/site/verify_site.py` (stack de pé em :3000)
"""

import os
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
# Prints de QA são efêmeros — vivem no temp do sistema, fora do repo.
OUT = Path(tempfile.gettempdir()) / "ritmo-site-qa"
# RITMO_BASE=http://localhost:3100 python scripts/site/verify_site.py
BASE = os.environ.get("RITMO_BASE", BASE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--hide-scrollbars"])

        for width, height, tag in [(390, 844, "mobile"), (1440, 900, "desktop")]:
            context = browser.new_context(
                viewport={"width": width, "height": height}, device_scale_factor=2
            )
            page = context.new_page()
            page.goto(f"{BASE}/", wait_until="load")
            assert page.url.rstrip("/") == BASE, f"landing desviou: {page.url}"
            page.wait_for_selector("img:visible", timeout=15_000)
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / f"site-{tag}.png"), full_page=True)
            print(f"ok site-{tag}.png (width {width})")

            # scroll horizontal não pode existir
            overflow = page.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            assert overflow <= 0, f"overflow horizontal de {overflow}px em {width}px"
            print(f"ok sem overflow horizontal ({width}px)")

            if width == 390:
                # visitante em rota de painel -> login com next
                page.goto(f"{BASE}/treinos", wait_until="load")
                assert "/login" in page.url, f"painel não protegeu: {page.url}"
                print(f"ok /treinos -> {page.url}")
            context.close()

        browser.close()
    print(f"QA ok — prints em {OUT.resolve()}")


if __name__ == "__main__":
    main()

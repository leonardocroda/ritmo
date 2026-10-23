"""Captura os prints reais da plataforma para o site (`public/site`).

Duas fases em uma execução:

1. **Login manual** — abre um Chromium visível em http://localhost:3000/login.
   Você digita email/senha (a senha não passa por script nenhum); quando a
   URL cai num painel (/treinos, /performance, /saude ou /perfil), o cookie
   de sessão é salvo em arquivo temporário FORA do repo e o navegador fecha.
2. **Captura** — Chromium headless com a sessão salva, viewport de
   390x844 (o mobile da identidade) em 2x de escala: prints do topo de
   cada painel (moldura de app) e prints de elemento dos cards-chave
   (gráficos, veredito da IA) para flutuar no layout do site.

Requisitos: stack de pé (frontend em :3000 com sessão válida após o
login) e `playwright` Python instalado (`pip install playwright`).

Uso: `python scripts/site/capture.py`
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
# frontend/scripts/site/capture.py -> frontend/public/prints
OUT = Path(__file__).resolve().parents[2] / "public" / "prints"
# Sessão fora do repo: cookie de usuário real, nunca versionado.
SESSION = Path(__file__).resolve().parents[3] / ".site-session.json"
PANELS = ("/treinos", "/performance", "/saude", "/perfil")
VIEWPORT = {"width": 390, "height": 844}
SCALE = 2  # retina: 780px de largura para uma moldura de 390px

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def say(msg: str) -> None:
    print(msg, flush=True)


def api_get(path: str, cookies: list[dict]) -> object:
    """GET na API com o cookie da sessão salva (mesma origem do rewrite)."""
    header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    req = urllib.request.Request(
        f"{BASE}{path}", headers={"Cookie": header, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.load(res)


def pick_workout(cookies: list[dict]) -> tuple[int, bool]:
    """Escolhe a corrida do print: preferência para uma com avaliação
    concluída (o card de veredito é o visual do recurso de IA); fallback
    para a primeira com voltas (o gráfico de splits é o herói do Treinos).
    """
    data = api_get("/api/activities?activity_type=running&limit=60", cookies)
    items = data["items"]
    for item in items:
        if not item["evaluated"]:
            continue
        detail = api_get(f"/api/activities/{item['id']}", cookies)
        evaluations = detail.get("evaluations") or []
        if evaluations and evaluations[0]["status"] == "done":
            return item["id"], True
    for item in items:
        detail = api_get(f"/api/activities/{item['id']}", cookies)
        if detail.get("splits"):
            return item["id"], False
    raise SystemExit("nenhuma corrida com voltas encontrada — rode um sync antes")


def wait_ready(page, selector: str, settle_ms: int = 2200) -> None:
    """Espera o conteúdo (dados do banco) + o assentamento dos gráficos
    Recharts (animação de entrada ~1,5s) e das fontes."""
    page.wait_for_selector(selector, state="visible", timeout=30_000)
    page.wait_for_timeout(settle_ms)
    page.evaluate("document.fonts.ready")


def shoot(page, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / name))
    say(f"  ok {name}")


def shoot_element(page, selector: str, name: str) -> None:
    el = page.locator(selector).first
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    OUT.mkdir(parents=True, exist_ok=True)
    el.screenshot(path=str(OUT / name))
    say(f"  ok {name}")


def login_and_save(p) -> list[dict]:
    say("abrimos o navegador — faça login em http://localhost:3000/login")
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 420, "height": 900}, device_scale_factor=1
    )
    page = context.new_page()
    page.goto(f"{BASE}/login")
    deadline = time.time() + 1200  # 20 min para o login manual
    while time.time() < deadline:
        if any(panel in page.url for panel in PANELS):
            break
        page.wait_for_timeout(500)
    else:
        browser.close()
        raise SystemExit("timeout: login não feito em 20 min")
    page.wait_for_timeout(1500)  # painel carrega antes de salvar
    state = context.storage_state(path=str(SESSION))
    browser.close()
    say(f"sessão salva em {SESSION}")
    return state["cookies"]


def capture(p, cookies: list[dict], workout_id: int) -> None:
    browser = p.chromium.launch(headless=True, args=["--hide-scrollbars"])
    context = browser.new_context(
        viewport=VIEWPORT, device_scale_factor=SCALE
    )
    context.add_cookies(cookies)
    page = context.new_page()

    def go(path: str) -> None:
        page.goto(f"{BASE}{path}", wait_until="load")

    # ---- Treinos: lista ----
    say("treinos — lista")
    go("/treinos")
    wait_ready(page, 'a[href^="/treinos/"]')
    shoot(page, "treinos-list.png")

    # ---- Treinos: detalhe do treino avaliado ----
    say(f"treinos — detalhe (id {workout_id})")
    go(f"/treinos/{workout_id}")
    wait_ready(page, "h1")
    shoot(page, "treino-detail.png")
    if page.locator('section:has(h2:text-is("Voltas"))').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Voltas")) div.rounded-card', "splits-chart.png")
    if page.locator('section:has(h2:text-is("Avaliação")) div.rounded-card').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Avaliação")) div.rounded-card', "evaluation-card.png")
    if page.locator('section:has(h2:text-is("Contexto do dia"))').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Contexto do dia"))', "contexto-dia.png")

    # ---- Performance ----
    say("performance")
    go("/performance")
    wait_ready(page, 'h2:text-is("Onde estou")')
    shoot(page, "performance-top.png")
    shoot_element(page, 'section:has(h2:text-is("Onde estou")) div.mt-3', "performance-vdot.png")
    if page.locator('section:has(h2:text-is("O que isso prevê"))').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("O que isso prevê")) div.mt-3', "predictions.png")
    if page.locator('section:has(h2:text-is("Carga de treino")) div.rounded-card').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Carga de treino")) div.rounded-card', "pmc-chart.png")

    # ---- Saúde ----
    say("saúde")
    go("/saude")
    wait_ready(page, 'h2:text-is("Sono")')
    shoot(page, "saude-top.png")
    if page.locator('section:has(h2:text-is("Sono")) div.rounded-card').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Sono")) div.rounded-card >> nth=0', "sleep-chart.png")
    if page.locator('section:has(h2:text-is("Recuperação")) div.rounded-card').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Recuperação")) div.rounded-card >> nth=0', "hrv-chart.png")
    if page.locator('section:has(h2:text-is("Dose-resposta"))').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Dose-resposta")) div.mt-3', "dose-response.png")

    # ---- Perfil (zonas de FC) ----
    say("perfil")
    go("/perfil")
    wait_ready(page, 'h2:text-is("Conexão Garmin")', settle_ms=1200)
    shoot(page, "perfil-top.png")
    if page.locator('section:has(h2:text-is("Valores")) div.mt-3').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Valores")) div.mt-3', "hr-values.png")
    if page.locator('section:has(h2:text-is("Método e zonas")) div.mt-3').count() > 0:
        shoot_element(page, 'section:has(h2:text-is("Método e zonas")) div.mt-3', "hr-zones.png")

    browser.close()
    say(f"prints em {OUT}")


def main() -> None:
    with sync_playwright() as p:
        cookies = login_and_save(p)
        workout_id, _ = pick_workout(cookies)
        say(f"treino do print: /treinos/{workout_id}")
        capture(p, cookies, workout_id)


if __name__ == "__main__":
    main()

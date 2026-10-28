#!/usr/bin/env python3
"""
Backfill Strava automatizado — OAuth + backfill em um comando.

Uso:
    uv run python scripts/strava_backfill_auto.py [--yes] [--user-id 1]

Lê STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET do backend/.env,
abre browser, captura code no callback localhost:8080,
troca por token e executa o backfill.
"""

import argparse
import os
import sys
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import httpx

# --- Carrega .env -----------------------------------------------------------
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        sys.exit(f"❌ .env não encontrado em {env_path}. Copie .env.example e preencha.")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

load_env()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
if not CLIENT_ID or not CLIENT_SECRET:
    sys.exit("ERRO: STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET não definidos no .env")

REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8080/callback")
SCOPE = "profile:read_all,activity:read_all"
AUTH_URL = (
    f"https://www.strava.com/oauth/authorize"
    f"?client_id={CLIENT_ID}"
    f"&response_type=code"
    f"&redirect_uri={REDIRECT_URI}"
    f"&approval_prompt=force"
    f"&scope={SCOPE}"
)

# --- Servidor local para capturar o code ------------------------------------
class CallbackHandler(BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            qs = parse_qs(parsed.query)
            print(f"[DEBUG] Callback received: {self.path}")
            if "code" in qs and CallbackHandler.code is None:
                CallbackHandler.code = qs["code"][0]
                print(f"[DEBUG] Code captured: {CallbackHandler.code[:20]}...")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html = """
                    <html><body style="font-family:sans-serif;text-align:center;padding:3rem">
                    <h2 style="color:#2e7d32">Autorizado!</h2>
                    <p>Pode fechar esta aba e voltar ao terminal.</p>
                    </body></html>
                """
                self.wfile.write(html.encode("utf-8"))
            elif "error" in qs:
                CallbackHandler.error = qs["error"][0]
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"<h2>Erro: {CallbackHandler.error}</h2>".encode())
            else:
                print(f"[DEBUG] Callback without code: {qs}")
                self.send_response(400)
                self.end_headers()
        else:
            print(f"[DEBUG] Other path: {self.path}")
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        pass  # silencia logs do servidor


def run_callback_server(port=8080, timeout=120):
    server = HTTPServer(("localhost", port), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"[+] Servidor callback rodando em http://localhost:{port}/callback")
    print(f"[+] AUTH_URL: {AUTH_URL}")
    print(f"[+] Abrindo browser para autorização...")

    webbrowser.open(AUTH_URL)

    # espera o code ou erro
    import time
    start = time.time()
    while CallbackHandler.code is None and CallbackHandler.error is None:
        if time.time() - start > timeout:
            server.shutdown()
            sys.exit("[!] Timeout: autorização não concluída em 120s")
        time.sleep(0.2)

    server.shutdown()

    if CallbackHandler.error:
        sys.exit(f"[!] Erro na autorização: {CallbackHandler.error}")

    print(f"[+] Code capturado: {CallbackHandler.code[:20]}...")
    return CallbackHandler.code


# --- Troca code por token ---------------------------------------------------
def exchange_code(code: str) -> str:
    print("[*] Trocando code por access_token...")
    resp = httpx.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"[!] Falha ao trocar code: {resp.status_code} - {resp.text}")
    data = resp.json()
    return data["access_token"]


# --- Executa backfill -------------------------------------------------------
def run_backfill(code: str, user_id: int, yes: bool):
    print("[*] Executando backfill...")
    # Importa o módulo de backfill e roda a função principal
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app.strava.backfill import run_backfill as backfill_main

    # Chama run_backfill com parâmetros nomeados (não objeto Args)
    backfill_main(code=code, token=None, user_id=user_id, yes=yes)


# --- Main -------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Backfill Strava automatizado (OAuth + backfill)")
    parser.add_argument("--yes", action="store_true", help="Pula confirmação interativa")
    parser.add_argument("--user-id", type=int, default=1, help="User ID no Ritmo (default: 1)")
    args = parser.parse_args()

    print("=" * 50)
    print("BACKFILL STRAVA AUTOMATIZADO")
    print("=" * 50)

    # 1. Captura code via OAuth
    code = run_callback_server()
    print(f"[+] Code recebido: {code[:10]}...")

    # 2. Roda backfill (ele troca o code por token internamente)
    run_backfill(code, args.user_id, args.yes)

    print("\n[+] Concluído!")


if __name__ == "__main__":
    main()
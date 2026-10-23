import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Proxy otimista de sessão (AD-018, feature auth): checa só a PRESENÇA
// do cookie de sessão — nunca valida o token. A API é a autoridade
// (require_session); aqui é UX de redirect antes de renderizar, padrão
// do guia de auth do Next 16 (middleware virou proxy na v16).

// Cookie setado pela API (settings.session_cookie_name) — host-only,
// visível aqui porque frontend e API estão no mesmo host (só a porta difere).
const SESSION_COOKIE = "ritmo_session";

// Telas protegidas (AUTH-17): painéis + /perfil (HRZ-16, feature
// hr-zones); `/` é a Home (home-panel, AD-025) — o next preserva a
// rota pedida, login devolve o usuário pra onde ele estava.
const PANEL_PREFIXES = ["/treinos", "/performance", "/saude", "/perfil"];
const AUTH_ROUTES = ["/login", "/registrar"];

function isPanelRoute(pathname: string): boolean {
  return (
    pathname === "/" ||
    PANEL_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"))
  );
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = request.cookies.has(SESSION_COOKIE);

  // Sem cookie em rota de painel → /login?next=<rota corrente> (AUTH-17).
  // O next preserva query e é URL-encoded; o login volta à rota original
  // — incluindo a raiz, que agora É o painel Home (AD-025).
  if (isPanelRoute(pathname) && !hasSession) {
    const next = pathname + search;
    return NextResponse.redirect(
      new URL(`/login?next=${encodeURIComponent(next)}`, request.nextUrl),
    );
  }

  // Autenticado em tela de auth → painéis (AUTH-19); sem next: é a
  // sessão falando, o destino natural é o painel principal — a Home.
  if (AUTH_ROUTES.includes(pathname) && hasSession) {
    return NextResponse.redirect(new URL("/", request.nextUrl));
  }

  return NextResponse.next();
}

// Roda em todas as rotas de página; exclui a API (proteção real é o
// require_session do backend), assets estáticos e favicon (convenção
// do guia de auth do Next 16).
export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};

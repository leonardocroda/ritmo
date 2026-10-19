# Auth Context

**Gathered:** 2026-10-19
**Spec:** `.specs/features/auth/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Contas próprias do Ritmo: registro com código de convite, login email+senha (argon2id),
sessão em banco via cookie HttpOnly, logout, proteção da API (401) e das telas (redirect),
bootstrap do usuário 1 via CLI e fixes de infraestrutura (sequência `users_pkey`, CORS
explícito). Fundação da Fase 1.5 (AD-012/013) — sem `/perfil`, sem zonas/LTHR no banco, sem
tokens Garmin, sem HTTPS.

---

## Implementation Decisions

### Sessão (decidido)

- **30 dias, sliding**: quando um request autenticado chega com ≤15 dias restantes, a
  validade vira +30 dias daquele request. Usuário ativo nunca é deslogado no meio do uso.
- Cookie `HttpOnly` + `SameSite=Lax`; `Secure` desligado porque o MVP roda em HTTP na LAN
  (Fase 2.5 traz HTTPS e liga o flag).
- Token de sessão: 32 bytes aleatórios; o banco guarda apenas o hash SHA-256 (vazamento do
  dump não reusa sessões).
- Sessões simultâneas permitidas (celular + PC); logout revoga só a sessão corrente.
- Sessões expiradas são removidas lazy no login do mesmo usuário (sem cron).

### Entrada e saída (decidido)

- Botão **Sair no header**, junto do SyncButton, com o display_name do usuário — única forma
  de revogação enquanto a `/perfil` não existe (feature 5 da fase).
- Telas `/login` e `/registrar` em layout mínimo, sem o header de painéis (nav/sync/conta).
- Erro de login: mensagem única genérica **"email ou senha inválidos"** — nunca revelar qual
  campo falhou.
- **Rate limit**: 5 falhas por email em 15 min → 429 com mensagem acionável; contador em
  memória (reinicia no restart — aceitável no MVP).
- **Volta à rota original pós-login**: `/login?next=<rota>`; sem `next`, aterrissa em
  `/treinos`. Client redireciona para `/login?next=...` ao receber 401 (sessão expirou em uso).
- **Pós-cadastro: auto-login** — register 201 já cria a sessão e entra nos painéis.
- Usuário autenticado que abre `/login` ou `/registrar` vai para `/treinos`.

### Convite e identidade (decidido)

- Código de convite fixo no env `INVITE_CODE`. **Vazio/ausente = registro desabilitado
  (403)** — o operador liga o convite só quando o `user-scope` estiver no ar, fechando a
  janela de interim em que um convidado veria o dataset único.
- Email case-insensitive (trim + lowercase normalizado), único; duplicate → 409.
- Senha mínima 8 caracteres, sem exigência de complexidade (argon2id segura o resto).
- `display_name` escolhido pelo convidado no cadastro (≤120, coluna existente).

### Infraestrutura (decidido)

- CLI `python -m app.auth.set_password` (email via input, senha via getpass): vincula o
  usuário seed (id 1, display_name "Leonardo" preservado) quando ele ainda não tem email;
  reset de suporte para contas existentes; cria conta nova para email desconhecido.
- Fix da sequência `users_pkey` no `init_db` (pendência do handoff) — o primeiro cadastro via
  app não pode colidir com o id 1 do seed.
- `CORS_ORIGINS` vira lista explícita (ex.: `http://localhost:3000,http://192.168.15.16:3000`);
  `allow_credentials=True` com `*` é rejeitado pelos browsers. Preflight OPTIONS isento de
  sessão.
- `GET /api/health` continua público (liveness, sem dado de usuário).

### Agent's Discretion

- **Mecânica de proteção no frontend** (middleware Next 16 vs. check de layout vs. handling
  de 401 no client): decisão de design — ler `frontend/node_modules/next/dist/docs/` antes de
  escrever código (regra do `frontend/AGENTS.md`: Next com breaking changes).
- Estrutura/nome do módulo `auth/` no backend (padrão de router/service já existente).
- Formato exato das mensagens de erro em PT-BR (consistente com o tom do app).
- Comparação constant-time do código de convite (higiene, custo zero).

### Declined / Undiscussed Gray Areas → Assumptions

Nenhuma recusada — os defaults apresentados no round de discussão (health público, interim
auth→user-scope, prune lazy, token hash, CORS explícito, preflight isento, display_name ≤120)
foram aceitos sem objeção e estão na tabela de Assumptions do spec, todos confirmados.

---

## Specific References

- Header atual: `SyncButton` global + nav de 3 painéis (Treinos · Performance · Saúde —
  AD-016/017); o par nome + "Sair" entra nesse header.
- Home já é redirect server-side para `/treinos` (`app/page.tsx`) — o comportamento autenticado
  (AUTH-20) preserva isso; o não-autenticado vira `/login`.
- Tema escuro, mobile-first 390px (UAT padrão do projeto) vale para as telas de auth.
- Padrão de testes: Postgres do compose (`ritmo_test`), schema dropado por teste, lifespan
  re-semeia o usuário 1 (`tests/conftest.py`).

---

## Deferred Ideas

- Checkbox "manter conectado" no login — desnecessário: a sessão sempre dura 30d sliding.
- Troca de senha na UI e reset self-service por email — `/perfil` (feature 5); por email não
  faz sentido sem SMTP (CLI resolve).
- Cookie Secure + HTTPS — Fase 2.5.
- Delete de conta / exportação LGPD — Fase 2.5.
- Papéis/admin e cota de IA por usuário — Fase 2.5/3.

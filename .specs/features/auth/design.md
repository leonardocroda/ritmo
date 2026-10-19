# Auth Design

**Spec**: `.specs/features/auth/spec.md`
**Context**: `.specs/features/auth/context.md`
**Status**: Draft

---

## Architecture Overview

Auth própria em duas camadas com responsabilidade única cada: a **FastAPI é a autoridade**
(cria/valida/revoga sessões, aplica 401) e o **Next 16 faz checagem otimista** (`proxy.ts`
olha só a *presença* do cookie para redirecionar antes de renderizar — nunca valida).
Frontend (:3000) e API (:8000) rodam no mesmo host e cookies ignoram porta → o cookie
host-only setado pela API é visível para o proxy E para os fetches do client. Sessão é
**stateful**: token opaco de 32 bytes no cookie, hash SHA-256 na tabela `sessions`.

```mermaid
graph TD
    A[Browser] -->|GET /treinos| P[proxy.ts - checagem otimista]
    P -->|sem cookie| L[/login?next=/treinos]
    P -->|com cookie| T[Painel renderiza]
    T -->|fetch + credentials| B[FastAPI require_session]
    P -->|/login com cookie| T
    B -->|cookie host-only :8000| C[(sessions - hash SHA-256)]
    B -->|401| W[api.ts wrapper]
    W -->|redirect| L
```

**Fluxos por AC**:

- **Sem sessão** → proxy redireciona para `/login?next=<rota>` (AUTH-17); API responderia 401
  de qualquer forma (AUTH-11) — o proxy é UX, a API é a garantia.
- **Sessão expirou em uso** → cookie está no browser mas o banco rejeitou → shell do painel
  carrega, o primeiro fetch volta 401 → wrapper do `api.ts` redireciona (AUTH-21). Único caso
  de flash de shell; cookie morto é aceitável (o token morreu no servidor).
- **Login/registro** → POST na API → `Set-Cookie` HttpOnly (host-only, SameSite=Lax) → client
  redireciona para `next` ou `/treinos` (AUTH-18/01).
- **Sair** → POST logout revoga a linha + limpa o cookie → `/login` (AUTH-24).

---

## Code Reuse Analysis

### Existing Components to Leverage

| Component | Location | How to Use |
| --- | --- | --- |
| Padrão router+service+schemas | `app/activities/`, `app/evaluation/` | Mesma estrutura para `app/auth/` |
| Padrão CLI com seam de teste | `app/garmin/login.py` (`run_login` com inputs injetáveis) | `app/auth/set_password.py` (input/getpass via monkeypatch) |
| `Settings` 100% env | `app/core/config.py` | Novas vars `INVITE_CODE`, `SESSION_*`, `CORS_ORIGINS` |
| `DEFAULT_USER_ID`/User seed | `app/db/models.py`, `app/db/engine.py` | Seed permanece; `init_db` ganha o `setval` |
| `ApiError` + `parseError` | `frontend/src/lib/api.ts` | Wrapper central ganha `credentials` + redirect 401 |
| Header/Nav/SyncButton | `frontend/src/components/` | Header ganha `UserMenu` (client); layout migra p/ route group |
| Redirect server-side da home | `frontend/src/app/page.tsx` | Preservado para autenticado (AUTH-20); proxy cobre o não-autenticado |
| Padrão de teste Postgres | `tests/conftest.py` | Novos testes de auth no mesmo banco `ritmo_test` |

### Integration Points

| System | Integration Method |
| --- | --- |
| Rotas existentes da API | `main.py` inclui cada router com `dependencies=[Depends(require_session)]` |
| CORS | `cors_origins` deixa de ser `*` — lista explícita via env (credentials exigem origem exata) |
| `users_pkey` | `setval` no `init_db` (pendência do handoff — resolve antes do 1º cadastro via app) |
| Frontend fetches (~10 call sites) | Todos migram para o wrapper com `credentials: "include"` |

---

## Components

### Backend — módulo `app/auth/`

#### `security.py`
- **Purpose**: primitivas criptográficas puras — hash/verify argon2id, geração e hash de token.
- **Interfaces**:
  - `hash_password(plain: str) -> str` — argon2id (argon2-cffi `PasswordHasher`)
  - `verify_password(plain: str, hashed: str) -> bool`
  - `new_session_token() -> str` — `secrets.token_urlsafe(32)` (~43 chars)
  - `hash_token(token: str) -> str` — SHA-256 hex (o que vai ao banco)
- **Dependencies**: `argon2-cffi` (nova dependência — única do feature no backend).
- **Reuses**: nada — funções puras, 100% testáveis.

#### `rate_limit.py`
- **Purpose**: contador em memória de falhas de login por email.
- **Interfaces**:
  - `check(email: str) -> None` — levanta `RateLimitedError` se ≥5 falhas em 15 min
  - `record_failure(email: str) -> None` / `reset(email: str) -> None` (sucesso zera)
  - `RateLimiter._store` — dict exposto para o fixture de teste zerar estado
- **Dependencies**: stdlib (`threading.Lock`, `time`).
- **Reuses**: nada. Interface trocável por Redis na Fase 2.5.

#### `service.py`
- **Purpose**: regras de negócio — registro, login, logout, me, renewal sliding, prune.
- **Interfaces**:
  - `register(db, payload, invite_from_env) -> tuple[User, str]` — valida convite/unicidade,
    cria user + sessão; devolve token cru (router seta o cookie). Erros: `InviteDisabledError`,
    `InviteInvalidError`, `EmailTakenError`
  - `login(db, email, password, limiter) -> tuple[User, str]` — 401 genérico nos dois ramos,
    429 via limiter; **prune lazy** das sessões expiradas do usuário (AUTH-16)
  - `create_session(db, user_id) -> str` — insere hash + `expires_at = now + 30d`
  - `resolve_session(db, token | None) -> User | None` — hash → lookup com
    `expires_at > now` → **renewal**: se restam ≤15d, `expires_at = now + 30d` e sinaliza
    renovação (AUTH-12); token ausente/inválido/expirado/revogado → None
  - `revoke(db, token | None) -> None` — delete da linha (idempotente)
- **Dependencies**: `security`, `rate_limit`, models.
- **Reuses**: `User`, `get_db`.

#### `deps.py`
- **Purpose**: dependência FastAPI que protege toda rota de dado.
- **Interfaces**:
  - `require_session(request, response, db) -> User` — resolve o cookie
    (`settings.session_cookie_name`), chama `resolve_session`; None → `HTTPException(401)`;
    renovação → re-seta o cookie no `response` injetado (Max-Age 30d — o cookie acompanha o
    sliding, senão o browser derruba a sessão antes do banco)
- **Dependencies**: `service.resolve_session`, `get_db`.
- **Reuses**: nada. Todos os routers existentes passam a listá-lo em `main.py`.

#### `router.py`
- **Purpose**: os 4 endpoints de auth (únicos públicos + `/me` protegido).
- **Interfaces**:
  - `POST /api/auth/register` → 201 `{id, email, display_name}` + Set-Cookie · 403 · 409 · 422
  - `POST /api/auth/login` → 200 `{id, email, display_name}` + Set-Cookie · 401 · 429
  - `POST /api/auth/logout` (protegido) → 204 + cookie expirado · 401
  - `GET /api/auth/me` (protegido) → 200 `{id, email, display_name}` · 401
- **Dependencies**: `service`, `deps` (logout/me), `settings`.
- **Reuses**: padrão de schemas Pydantic dos outros routers.

#### `set_password.py`
- **Purpose**: CLI de bootstrap/suporte — `uv run python -m app.auth.set_password`.
- **Interfaces**:
  - `main()` — email via `input`, senha via `getpass`; vincula o usuário seed (id 1 sem
    email) preservando display_name; reset para email existente; cria conta para email novo
    quando o seed já tem email
  - `run_set_password(email, password) -> User` — seam de teste (padrão `run_login`)
- **Dependencies**: `security`, models, `SessionLocal`.
- **Reuses**: padrão do `app/garmin/login.py` (`__main__` guard, inputs injetáveis).

### Infra backend

#### `app/db/models.py` — mudanças
- `User`: `email: Mapped[str | None]` (String(255), **unique**, nullable — seed id 1 nasce sem
  email até o CLI vinculá-lo; Postgres permite múltiplos NULL em unique) e
  `password_hash: Mapped[str | None]`.
- Nova `UserSession` (`__tablename__ = "sessions"` — nome da classe evita colisão com
  `sqlalchemy.orm.Session`): `id`, `user_id` FK (CASCADE), `token_hash` String(64) **unique**
  index, `expires_at` DateTime index, `created_at`. Logout = DELETE (sem flag), tabela fica
  mínima.

#### `app/core/config.py` — novas settings
- `invite_code: str = ""` (vazio = registro desabilitado)
- `session_ttl_days: int = 30` · `session_renew_threshold_days: int = 15`
- `session_cookie_name: str = "ritmo_session"` · `session_cookie_secure: bool = False` (LAN;
  Fase 2.5 liga)
- `cors_origins`: default muda de `"*"` para `"http://localhost:3000"` (documentar override no
  `.env.example` com o IP da LAN — ex.: `http://192.168.15.16:3000`)

#### `app/db/engine.py` — `init_db()`
- Após o seed: `SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id),1) FROM users))` via
  `text()` — Postgres-only por decisão (AD-007). Corrige a sequência desincronizada
  (pendência do handoff) para o primeiro cadastro via app.

#### `app/main.py`
- `include_router(auth_router)` + todos os routers existentes ganham
  `dependencies=[Depends(require_session)]`; `/api/health` fica fora (público).

### Frontend

#### `src/proxy.ts`
- **Purpose**: checagem otimista de rota (presença do cookie — **nunca** valida token).
- **Comportamento**: pathname protegido (`/`, `/treinos/*`, `/performance`, `/saude`) sem
  cookie → redirect `/login?next=<pathname+search>` (URL-encoded); `/login`/`/registrar` com
  cookie → redirect `/treinos`; resto → next(). Matcher exclui `/api/:path*`, `_next/static`,
  `_next/image`, favicon (convenção do guia de auth do Next 16 — proxy roda em todas as
  rotas de página).
- **Reuses**: convenção do Next 16 (middleware renomeado para proxy — `16-proxy.md`).

#### Route groups — `src/app/(app)/` e `src/app/(auth)/`
- `(app)`: recebe `layout.tsx` atual (Header) + `page.tsx` (redirect `/`→`/treinos`) +
  `treinos/`, `performance/`, `saude/`. URLs não mudam.
- `(auth)`: `login/` e `registrar/` com layout mínimo sem Header (AUTH-22).
- Reuses: estrutura existente apenas movida (git mv).

#### `src/lib/api.ts` — wrapper central
- **Purpose**: todo fetch sai daqui com `credentials: "include"` + tratamento de 401.
- **Interfaces**:
  - `apiFetch(path, init) -> Response` — injeta `credentials: "include"`;
    se 401 e o path **não** é `/api/auth/*` e o browser não está em `/login` →
    `window.location.replace("/login?next=" + encodeURIComponent(location.pathname + search))`
  - `login(email, password)`, `register(payload)`, `logout()`, `me()` — novos helpers
  - ~10 call sites existentes migram de `fetch` direto para `apiFetch`
- **Reuses**: `parseError`/`ApiError` existentes.

#### `src/components/UserMenu.tsx`
- **Purpose**: chip do usuário no header — display_name + botão "Sair".
- **Comportamento**: monta → `me()` (via wrapper); sucesso → renderiza; 401 → não renderiza
  (o proxy/API cuidam do redirect). "Sair" → `logout()` → `location.assign("/login")`.
- **Reuses**: Header (server component) renderiza este client component.

#### Telas `(auth)/login/page.tsx` e `(auth)/registrar/page.tsx`
- Forms client components (email/senha/código de convite/nome); erro do backend exibido
  inline (mensagem PT-BR vinda do `detail`); sucesso → `router.replace(next ?? "/treinos")`.
- Tema escuro/mobile-first 390px existente.

---

## Data Models

### User (alteração)

```python
email: str | None        # String(255), unique, nullable — normalizado lowercase no service
password_hash: str | None  # String(255) — argon2id
```

### UserSession (tabela `sessions`, nova)

```python
id: int
user_id: int          # FK users.id, ondelete CASCADE
token_hash: str       # String(64) hex SHA-256 — unique, index
expires_at: datetime  # now + 30d; sliding move para now + 30d quando restam ≤15d
created_at: datetime
```

**Relationships**: `user_id → users.id` (CASCADE — deletar usuário derruba as sessões).

---

## Error Handling Strategy

| Error Scenario | Handling | User Impact |
| --- | --- | --- |
| Rota de dado sem sessão | Proxy redireciona `/login?next=`; API responderia 401 | Vai ao login sem ver conteúdo |
| Sessão revogada/expirada com cookie no browser | Shell carrega, 1º fetch 401 → wrapper redireciona | Flash de shell uma vez, depois login |
| Credenciais erradas | 401 "email ou senha inválidos" (único para os dois ramos) | Mensagem genérica inline no form |
| 5 falhas / 15 min | 429 com mensagem da janela | Inline no form; passa em 15 min |
| Convite desabilitado/errado | 403 com a mensagem específica | Inline no form de registro |
| Email duplicado (case-variant) | 409 | Inline no form |
| Payload inválido (senha <8, email malformado, nome >120) | 422 campo a campo | Inline por campo |
| Logout sem sessão | 401 (operação protegida) | Client já está indo pro /login |
| Backend fora | fetch falha (network) | Painel mostra erro; sem redirect falso |
| Origem fora de `CORS_ORIGINS` | Sem headers CORS (browser bloqueia) | Não afeta os acessos documentados (localhost/LAN IP) |

---

## Risks & Concerns

| Concern | Location | Impact | Mitigation |
| --- | --- | --- | --- |
| Cookie host-only exige **mesmo host** entre frontend e API (só a porta difere) | deploy (compose/README) | Acessar o frontend por host ≠ `NEXT_PUBLIC_API_URL` (ex.: `localhost:3000` com API no IP LAN) quebra o cookie → loop de redirect | Constraint documentada no README §LAN e no `.env.example` (comportamento de cookies; compose default já é consistente) |
| Rate limiter em memória compartilha estado entre testes do TestClient | `app/auth/rate_limit.py` | Falso 429 na suite | Fixture autouse zera `_store` (mesmo padrão do `_clean_database`) |
| `setval` no `init_db` é Postgres-only | `app/db/engine.py` | Nenhum — AD-007 tornou Postgres o único dialeto; suite já exige o compose | Nenhuma ação extra |
| Movimentação de páginas para route groups pode afetar o Suspense do `usePathname` | `frontend/src/components/Nav.tsx` | Nav deixa de marcar ativo se a boundary quebrar | Route groups não mudam URLs nem o pathname; UAT confere a marcação do painel ativo |
| Flash de shell quando o cookie está morto no browser (revogado/expirado) | proxy (por design) | UX degradada uma vez até o redirect do wrapper | Aceito: proxy não consulta banco (padrão Next); caso raro e auto-corrigido |
| Renovação sliding escreve no banco em GET | `app/auth/deps.py` | 1 UPDATE só quando restam ≤15d (não por request) | Threshold evita escrita frequente; custo irrelevante na escala |
| XSS via texto de LLM nos vereditos | frontend | Sequestrar sessão se houvesse injeção | React escapa por padrão; zero `dangerouslySetInnerHTML`/`innerHTML` no código (verificado); cookie HttpOnly mantém o token fora do JS |
| Frontend sem test runner | `frontend/package.json` | ACs de tela sem gate automático | Padrão do projeto: UAT no celular (390px) com evidência; backend cobre 401s/erros via pytest |

---

## Tech Decisions (only non-obvious ones)

| Decision | Choice | Rationale |
| --- | --- | --- |
| Modelo de sessão | **Stateful** — token opaco 32B + hash SHA-256 em `sessions` | Revogação (Sair), sliding e kill-switch de senha triviais; JWT exigiria denylist/re-emissão/token_version para o mesmo resultado. Ganho do stateless (escala horizontal, sem lookup) não existe neste deploy (1 container, Postgres no mesmo host). Decisão **de projeto** → AD-018 |
| Proteção de telas | **API autoritativa + proxy otimista** | Padrão do guia de auth do Next 16; sem BFF (reescreveria o fluxo client→API por ganho nulo) e sem depender só do 401 (fere AUTH-17). Decisão **de projeto** → AD-018 |
| Hash de senha | `argon2-cffi` direto (não passlib) | passlib sem manutenção estável com bcrypt moderno; argon2id é o padrão atual e a API da lib é trivial |
| Cookie | Host-only (sem `Domain`), `HttpOnly`, `SameSite=Lax`, `Max-Age=30d`, `Secure` por env | Host-only é o que habilita o mesmo cookie no proxy (:3000) e na API (:8000); sliding re-seta o cookie no limiar para o browser acompanhar o banco |
| Email único | Coluna lowercase normalizada + `unique=True` (não índice functional) | Normalização no service; índice simple + múltiplos NULL (seed sem email) funcionam |
| Proteção dos routers | `dependencies=[...]` explícitos por include no `main.py` | Visível no entrypoint (o mapa do que é público está num arquivo); sem middleware global que esconda exceções |
| Fix da sequência | `setval` no `init_db` (não migração) | `create_all` já é o mecanismo de schema do projeto; o fix acompanha o seed |
| Re-emissão de token no sliding | Não — só `expires_at` + re-set do cookie (mesmo token) | Token opaco não carrega expiração assinada; re-emitir seria custo sem ganho |

---

## Test Strategy

- **Backend (pytest, Postgres do compose)**: fluxo register→me→logout→401; erros 403/409/422/429
  (fixture zera o limiter); sliding (manipula `expires_at` para o limiar e confere renovação);
  401 sem cookie em endpoint protegido (pinado); `/api/health` público; preflight OPTIONS
  isento; `setval` (register duplo sem colisão); CLI com seam (`run_set_password` monkeypatched).
- **Frontend (UAT no celular, 390px — padrão do projeto)**: sem sessão → `/login?next=`;
  login volta à rota original; Sair revoga (voltar não reabre); logado em `/login` →
  `/treinos`; layout mínimo das telas de auth.

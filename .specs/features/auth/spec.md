# Auth Specification

## Problem Statement

A API e as telas do Ritmo estão abertas na LAN: qualquer dispositivo com a URL lê treinos e
dados de saúde, dispara sync e consome avaliação de IA (custo por chamada). A Fase 1.5
(AD-012) precisa de identidade por usuário como fundação para zonas/LTHR/tokens Garmin por
usuário e para o MVP de 5–20 convidados. Decisões de produto travadas: auth próprio
self-hosted (AD-013), cadastro por código de convite, CLI de bootstrap, sessão sliding de
30 dias, Sair no header.

## Goals

- [ ] Nenhuma tela ou endpoint de dado responde sem sessão válida (telas → `/login`; API → 401)
- [ ] Leonardo e convidados com o código de convite criam conta e entram; a sessão sobrevive
      30 dias de uso contínuo (sliding) sem re-login
- [ ] Infra pronta para cadastro via app: sequência `users_pkey` corrigida e CORS explícito
      com credenciais

## Out of Scope

| Feature | Reason |
| --- | --- |
| `/perfil` (nome, troca de senha, zonas, status Garmin) | Feature 5 da Fase 1.5 |
| Zonas VDOT / LTHR por usuário no banco | Feature 3 (`zones-db`) |
| Tokens Garmin no banco (cofre Fernet) | Feature 4 (`garmin-tokens-db`) |
| HTTPS / cookie Secure | MVP roda na LAN (AD-012); Fase 2.5 |
| Troca de senha na UI; reset self-service por email | `/perfil` (Fase 1.5); reset hoje = CLI |
| Delete de conta / exportação LGPD | Fase 2.5 |
| Fluxo web de credenciais Garmin | Fase 3 (AD-014) |
| Papéis/admin, cota de IA por usuário | Sem necessidade no MVP; Fase 2.5/3 |
| Mudança no comportamento do sync/painéis por usuário | Feature 2 (`user-scope`); interim coberto por assumption |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| `INVITE_CODE` ausente/vazio | Registro desabilitado (403) | Operador liga o convite só quando `user-scope` estiver no ar — fecha a janela em que um convidado veria o dataset único (usuário 1) | y |
| Política de senha | Mínimo 8 caracteres, sem exigência de complexidade | LAN entre amigos; argon2id faz o trabalho pesado | y |
| Rate limit do login | 5 falhas / 15 min por email (em memória) → 429 | Trava força-bruta básica; reinicia no restart do backend — aceitável no MVP | y |
| `/api/health` | Continua público (liveness, sem dado de usuário) | `curl` do README segue funcionando; compose não tem healthcheck HTTP do backend | y |
| Email | Case-insensitive (lowercase normalizado), único | Identidade canônica simples | y |
| Sessões simultâneas | Permitidas (celular + PC); Sair revoga só a corrente | Realidade de uso | y |
| Erro de login | Mensagem única genérica "email ou senha inválidos" | Não revela qual campo falhou | y |
| Interim auth → user-scope | Painéis/sync seguem operando sobre o dataset do usuário 1 para qualquer sessão | Transitório (~dias); registro desabilitado (assumption 1) fecha o risco | y |
| Sessões expiradas | Prune lazy no login do mesmo usuário; sem cron | Housekeeping sem operação extra | y |
| Cookie | `HttpOnly`, `SameSite=Lax`, `Secure` desligado (LAN HTTP) | Fase 2.5 traz HTTPS e liga Secure | y |
| CORS | Lista explícita via `CORS_ORIGINS` (ex.: `localhost:3000` + IP LAN `:3000`) | `allow_credentials` com `*` é rejeitado pelos browsers | y |
| Preflight OPTIONS | Isento de sessão | CORS preflight nunca carrega cookie de forma confiável | y |
| Token de sessão | 32 bytes aleatórios; banco guarda só o hash SHA-256 | Vazamento do dump do banco não reusa sessões | y |
| `display_name` | Definido pelo convidado no cadastro, ≤120 (coluna existente) | Campo já existe no schema | y |

**Open questions:** none — all resolved or logged above (required before the spec is confirmed).

---

## User Stories

### P1: Cadastro por convite ⭐ MVP

**User Story**: As a convidado com código de convite, I want criar minha conta (nome, email,
senha) e já entrar logado so that eu use os painéis sem depender do operador.

**Why P1**: Onboarding dos 5–20 convidados sem UI de admin; auto-login fecha o fluxo em um passo.

**Acceptance Criteria**:

1. WHEN `POST /api/auth/register` recebe código de convite válido, email inédito, senha ≥8 e
   display_name válido THEN o sistema SHALL criar a conta (email gravado em lowercase) e
   responder 201 com cookie de sessão (auto-login)  <!-- event-driven -->
2. IF `INVITE_CODE` estiver ausente ou vazio THEN `register` SHALL responder 403
   "registro desabilitado", independentemente do payload  <!-- unwanted-behavior -->
3. IF o código enviado diferir de `INVITE_CODE` THEN `register` SHALL responder 403
   "código de convite inválido"  <!-- unwanted-behavior -->
4. IF o email (após lowercase) já pertencer a uma conta THEN `register` SHALL responder 409
   "email já cadastrado"  <!-- unwanted-behavior -->
5. IF senha <8, email malformado ou display_name vazio/>120 THEN `register` SHALL responder
   422 com mensagem específica do campo violado  <!-- unwanted-behavior -->

**Independent Test**: com `INVITE_CODE` no env, `curl` de register → 201 + cookie; repetir o
mesmo email → 409; código errado → 403; sem env → 403; senha curta → 422.

---

### P1: Login e logout ⭐ MVP

**User Story**: As a usuário cadastrado, I want entrar com email+senha e sair quando quiser
so that eu controle quem usa cada dispositivo.

**Why P1**: Base da sessão; sem logout acessível, a sessão de 30d fica presa no dispositivo.

**Acceptance Criteria**:

1. WHEN `POST /api/auth/login` recebe credenciais válidas THEN o sistema SHALL responder 200 e
   setar o cookie de sessão `HttpOnly` + `SameSite=Lax`  <!-- event-driven -->
2. IF o email não existe ou a senha está errada THEN o login SHALL responder 401 com a
   mensagem única "email ou senha inválidos"  <!-- unwanted-behavior -->
3. IF houver ≥5 falhas de login do mesmo email em 15 min THEN o login SHALL responder 429 até
   a janela passar — mesmo com senha correta  <!-- unwanted-behavior -->
4. WHEN `POST /api/auth/logout` chega com sessão válida THEN o sistema SHALL revogar essa
   sessão, limpar o cookie e responder 204  <!-- event-driven -->
5. WHEN `GET /api/auth/me` chega com sessão válida THEN o sistema SHALL responder 200 com
   `{id, email, display_name}`  <!-- event-driven -->

**Independent Test**: register → login → me 200; logout → me 401 e cookie inutilizado;
5 senhas erradas → 429.

---

### P1: Sessão sliding + proteção da API ⭐ MVP

**User Story**: As a usuário logado, I want permanecer logado por 30 dias de uso sem re-login
so that o app não me expulsa no meio do bloco — e ninguém sem sessão toque na API.

**Why P1**: É a garantia de isolamento mínima desta feature; o escopo por usuário vem depois.

**Acceptance Criteria**:

1. WHILE um request `/api/*` (exceto `GET /api/health`, `POST /api/auth/register`,
   `POST /api/auth/login` e OPTIONS) não carrega sessão válida, o sistema SHALL responder 401
   JSON sem nenhum dado  <!-- state-driven -->
2. WHEN um request autenticado chega com a sessão tendo ≤15 dias restantes THEN o sistema
   SHALL estender a validade para 30 dias a partir desse request (sliding)  <!-- complex -->
3. IF o token está expirado (>30 dias sem renovação) ou revogado THEN qualquer endpoint
   protegido SHALL responder 401  <!-- unwanted-behavior -->
4. O cookie de sessão SHALL ser `HttpOnly` e `SameSite=Lax` (inacessível ao JS)  <!-- ubiquitous -->
5. O banco SHALL guardar apenas o hash SHA-256 do token de sessão, nunca o token  <!-- ubiquitous -->
6. WHEN um login é bem-sucedido THEN o sistema SHALL remover as sessões expiradas do mesmo
   usuário (prune lazy)  <!-- event-driven -->

**Independent Test**: `GET /api/activities` sem cookie → 401; com cookie → 200; `expires_at`
no passado → 401; renewal conferido no banco após request com <15d restantes.

---

### P1: Proteção das telas e navegação de auth ⭐ MVP

**User Story**: As a dono dos dados, I want que nenhuma tela mostre conteúdo sem sessão
so that o celular de um amigo nunca abra meus dados por acidente.

**Why P1**: A fronteira visível da auth; é o que o convidado e o dono experimentam.

**Acceptance Criteria**:

1. WHEN um usuário sem sessão abre `/treinos`, `/performance`, `/saude`, `/treinos/[id]` ou
   `/` THEN o sistema SHALL aterrissar em `/login` sem renderizar conteúdo de painel
   <!-- event-driven -->
2. WHEN o login é concluído a partir de `/login?next=<rota>` THEN o usuário SHALL aterrissar
   em `<rota>`; sem `next`, em `/treinos`  <!-- event-driven -->
3. WHEN um usuário autenticado abre `/login` ou `/registrar` THEN o sistema SHALL redirecionar
   para `/treinos`  <!-- event-driven -->
4. WHEN um usuário autenticado abre `/` THEN o sistema SHALL redirecionar para `/treinos`
   (comportamento atual preservado)  <!-- event-driven -->
5. WHEN qualquer chamada `/api/*` do client recebe 401 (ex.: sessão expirou em uso) THEN o
   client SHALL redirecionar para `/login` com `next` = rota corrente  <!-- event-driven -->
6. As telas `/login` e `/registrar` SHALL renderizar em layout mínimo, sem o header de
   painéis (nav/sync/conta)  <!-- ubiquitous -->

**Independent Test**: abrir `/performance` logado-out no celular (390px) → `/login`; logar →
volta para `/performance`; voltar logado ao `/login` → `/treinos`.

---

### P1: Sair no header ⭐ MVP

**User Story**: As a usuário logado, I want um controle "Sair" sempre visível
so that eu revogue a sessão deste dispositivo (ex.: celular emprestado).

**Why P1**: Única forma de revogação enquanto a `/perfil` não existe (feature 5 da fase).

**Acceptance Criteria**:

1. WHILE autenticado, o header SHALL exibir o display_name do usuário e o controle "Sair"
   <!-- state-driven -->
2. WHEN o usuário clica "Sair" THEN o client SHALL chamar `POST /api/auth/logout` e aterrissar
   em `/login`  <!-- event-driven -->

**Independent Test**: clicar Sair no celular → `/login`; abrir `/treinos` em seguida →
continua em `/login` (sessão revogada no servidor).

---

### P1: Bootstrap do usuário 1 + fixes de infraestrutura ⭐ MVP

**User Story**: As a operador (Leonardo), I want definir minha senha via CLI sem UI de admin
so that a conta seed ganha credenciais e o cadastro via app funciona sem erro de sequência.

**Why P1**: Sem isso, ninguém (nem o dono) entra; e o primeiro cadastro via app colide com a
sequência `users_pkey` desincronizada (pendência conhecida do handoff).

**Acceptance Criteria**:

1. WHEN `python -m app.auth.set_password` roda com um email que nenhuma conta possui THEN o
   sistema SHALL criar a conta com esse email e senha; IF o usuário seed (id 1) ainda não tem
   email, o sistema SHALL vinculá-lo a ele preservando o display_name  <!-- complex -->
2. WHEN o CLI roda para um email de conta existente THEN o sistema SHALL substituir o hash da
   senha sem alterar display_name (reset de suporte)  <!-- event-driven -->
3. WHEN um usuário é criado via app (register) THEN o INSERT SHALL ter sucesso sem erro de
   duplicate key (sequência `users_pkey` corrigida no `init_db`) e o id SHALL ser novo (>1)
   <!-- event-driven -->
4. WHEN um request credenciado chega de origem listada em `CORS_ORIGINS` THEN a resposta SHALL
   conter essa origem exata (não `*`) + `allow-credentials`; origem fora da lista SHALL não
   receber headers CORS  <!-- event-driven -->

**Independent Test**: CLI define a senha do usuário seed → login funciona; segundo usuário
criado via register recebe id >1 sem colisão; preflight OPTIONS de origem permitida → 200 com
headers CORS exatos.

---

## Edge Cases

- IF o email chega com maiúsculas/espaços THEN o register SHALL normalizar (trim + lowercase)
  antes de checar unicidade (complementa AUTH-01)
- IF a sessão expira no meio do uso (abas abertas de madrugada) THEN a próxima chamada da UI
  SHALL receber 401 e redirecionar para `/login` com `next` (AUTH-21)
- IF dois dispositivos usam a mesma conta THEN ambos SHALL permanecer logados; Sair em um
  SHALL revogar apenas a sessão daquele dispositivo (AUTH-06/09 + assumption)
- WHEN o rate limit dispara THEN o 429 SHALL informar que há tentativas demais e que a janela
  é de 15 minutos (mensagem acionável, PT-BR)
- IF `GET /api/auth/me` chega sem sessão THEN SHALL responder 401 (cobre AUTH-11 — `/me` não
  está na lista de exceção)
- IF o convidado acessa uma rota deletada (ex.: `/hoje`) THEN o 404 natural do Next SHALL
  prevalecer — fora do escopo desta feature (rota não existe, AD-016)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| AUTH-01 | P1: Cadastro por convite | - | Pending |
| AUTH-02 | P1: Cadastro por convite | - | Pending |
| AUTH-03 | P1: Cadastro por convite | - | Pending |
| AUTH-04 | P1: Cadastro por convite | - | Pending |
| AUTH-05 | P1: Cadastro por convite | - | Pending |
| AUTH-06 | P1: Login e logout | - | Pending |
| AUTH-07 | P1: Login e logout | - | Pending |
| AUTH-08 | P1: Login e logout | - | Pending |
| AUTH-09 | P1: Login e logout | - | Pending |
| AUTH-10 | P1: Login e logout | - | Pending |
| AUTH-11 | P1: Sessão sliding + proteção da API | - | Pending |
| AUTH-12 | P1: Sessão sliding + proteção da API | - | Pending |
| AUTH-13 | P1: Sessão sliding + proteção da API | - | Pending |
| AUTH-14 | P1: Sessão sliding + proteção da API | - | Pending |
| AUTH-15 | P1: Sessão sliding + proteção da API | - | Pending |
| AUTH-16 | P1: Sessão sliding + proteção da API | - | ✅ Verified |
| AUTH-17 | P1: Proteção das telas e navegação de auth | - | Pending |
| AUTH-18 | P1: Proteção das telas e navegação de auth | - | Pending |
| AUTH-19 | P1: Proteção das telas e navegação de auth | - | Pending |
| AUTH-20 | P1: Proteção das telas e navegação de auth | - | Pending |
| AUTH-21 | P1: Proteção das telas e navegação de auth | - | Pending |
| AUTH-22 | P1: Proteção das telas e navegação de auth | - | Pending |
| AUTH-23 | P1: Sair no header | - | Pending |
| AUTH-24 | P1: Sair no header | - | Pending |
| AUTH-25 | P1: Bootstrap do usuário 1 + fixes | - | Pending |
| AUTH-26 | P1: Bootstrap do usuário 1 + fixes | - | Pending |
| AUTH-27 | P1: Bootstrap do usuário 1 + fixes | - | ✅ Verified |
| AUTH-28 | P1: Bootstrap do usuário 1 + fixes | - | Pending |

**Coverage:** 28 total, 28 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] No celular via LAN (390px), abrir qualquer painel sem sessão aterrissa no `/login`; após
      logar, volta à rota original
- [ ] Convidado com o código de convite cria conta, entra auto-logado e navega; "Sair" revoga
      a sessão no servidor (voltar não reabre o painel)
- [ ] Sessão sobrevive a 30 dias de uso com renewal sliding; sem uso por 30 dias, exige login
- [ ] Suite completa verde no Postgres do compose — incluindo testes de proteção (401 sem
      sessão) e de rate limit
- [ ] `curl http://localhost:8000/api/health` continua 200 sem sessão

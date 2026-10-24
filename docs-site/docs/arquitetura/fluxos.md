# Arquitetura — Fluxos

Quatro fluxos explicam o tempo de vida de cada ação importante do sistema.
As state machines de sync e avaliação estão nas páginas de
[Sync Garmin](../backend/garmin-sync.md) e [Avaliação com IA](../backend/avaliacao-ia.md).

## 1. Request de painel (transporte same-origin, AD-020)

Todo fetch do frontend usa base relativa (`API_BASE = ""`). O Next entrega
em `BACKEND_URL` — o cookie de sessão vale para o host que o usuário abriu,
e o CORS deixa de ser requisito do fluxo normal.

```mermaid
sequenceDiagram
    actor U as Usuário (navegador)
    participant N as Next.js (Vercel/compose)
    participant A as FastAPI (Render/compose)
    participant D as Postgres

    U->>N: GET /api/health/summary?days=60 (com cookie)
    Note over N: rewrite same-origin<br/>/api/* → BACKEND_URL
    N->>A: GET /api/health/summary?days=60
    A->>A: require_session — hash SHA-256 do cookie
    A->>D: sessão válida? (expires_at > now)
    D-->>A: user_id
    A->>D: queries user-scoped
    D-->>A: linhas
    A-->>N: 200 JSON (payload espelha o painel, AD-009)
    N-->>U: 200 JSON
    Note over U,A: cookie ausente/expirado: A responde 401<br/>e o client redireciona /login?next=<rota>
```

## 2. Sync do Garmin

O job roda em `BackgroundTasks` — o client recebe `201` na hora e polla o
status a cada 2s. Fases em sequência rígida (nunca concorrentes):

```mermaid
sequenceDiagram
    actor U as Usuário
    participant F as Frontend (/perfil)
    participant A as FastAPI
    participant Gw as GarminGateway
    participant Gm as Garmin Connect
    participant D as Postgres

    U->>F: clique "Puxar do Garmin"
    F->>A: POST /api/sync
    A->>D: sync_jobs status=running<br/>(índice parcial: 1 job ativo/user)
    A-->>F: 201 {job_id}
    loop polling a cada 2s
        F->>A: GET /api/sync/jobs/latest
        A-->>F: status + contadores (progresso no botão)
    end
    Note over A: BackgroundTasks — job sequencial
    A->>Gw: run_sync(user_id, janela)
    Gw->>D: tokens Fernet decifrados (garmin_tokens)
    Gw->>Gm: login por blob de tokens (sem senha)
    Gw->>Gm: 1. atividades (paginado) + splits por corrida
    Gw->>D: upsert activities + splits — UMA transação
    Gw->>Gm: 2. sono · 3. HRV · 4. RHR · 5. estresse (1 chamada/dia)
    Gw->>Gm: 6. body battery (blocos de até 28 dias)
    Gw->>Gm: 7. recordes + 8. predições (1 chamada cada)
    Gw->>Gm: 9. physio: zonas de FC (fcmax) + LTHR (fclthr)
    Gw->>D: 10. PMC recompute (local) + fcrest (mín. 7d da série rhr)
    Gw->>D: 11. persist-back do token rotacionado<br/>(guard otimista updated_at)
    Gw-->>A: stats + warnings
    A->>D: sync_jobs status=done
    F->>A: GET (último polling)
    A-->>F: done — resumo PT-BR no botão
```

Casos de erro (o job nunca fica mudo):

- **Token expirado** (401): nenhuma tentativa de retry — job `error` com
  `reauth_needed: true`; o botão vira **Reconectar Garmin** com a
  instrução da CLI (a UI nunca pede credenciais, AD-014).
- **Teto de chamadas** (`SYNC_MAX_CALLS`) ou falha persistente: job
  `error` com o motivo.
- **Falha de um tipo de saúde**: vira warning em `stats_json` e o job
  segue (a fase 1 — atividades — é a única crítica: falha nela =
  rollback integral).
- **Restart do backend**: `recover_stale_jobs()` no startup marca jobs
  órfãos como `error` ("interrompido por restart").

## 3. Avaliação com IA

O POST grava a linha `pending` e responde `201` na hora; a NIM roda em
background e o client polla a cada 2s.

```mermaid
sequenceDiagram
    actor U as Usuário
    participant F as Frontend (/treinos/[id])
    participant A as FastAPI
    participant N as NVIDIA NIM
    participant D as Postgres

    U->>F: intenção (tipo + texto) → "Avaliar com IA"
    F->>A: POST /api/activities/{id}/evaluate
    A->>D: monta payload determinístico<br/>(100% do banco, AD-003)
    A->>D: evaluations status=pending<br/>(payload, model, prompt_version)
    A-->>F: 201 {evaluation_id}
    loop polling a cada 2s
        F->>A: GET .../evaluate/{evaluation_id}
        A-->>F: pending → card "Analisando treino…"
    end
    Note over A: BackgroundTasks — worker
    A->>N: chat/completions (glm-5.3, temp 0.2,<br/>timeout 420s)
    N-->>A: JSON de veredito
    A->>A: valida contrato §9.2 +<br/>sobrescreve pct_zona_alvo (anti-eco)
    A->>D: verdict, tokens_in/out, status=done,<br/>activities.evaluated=true
    F->>A: GET (polling)
    A-->>F: done → card do veredito
```

Falhas viram `status=error` **com o motivo gravado na linha** (timeout,
429, JSON fora do contrato) — a tentativa nunca se perde, e não há retry
automático (cada pedido custa tokens). Re-avaliar cria linha nova; o
card mostra sempre a mais recente e o histórico lista as anteriores.

## 4. Login e sessão (stateful, AD-018)

```mermaid
sequenceDiagram
    actor U as Usuário
    participant P as proxy.ts (Next)
    participant A as FastAPI
    participant D as Postgres

    Note over P: visita /treinos sem cookie
    P->>U: redirect /login?next=/treinos (UX)
    U->>A: POST /api/auth/login {email, senha}
    A->>A: rate limit 5 falhas/15min por email → 429
    A->>D: argon2id verify (hash) + email único
    A->>D: sessions ← token opaco de 32 bytes<br/>(só o hash SHA-256 é gravado)
    A-->>U: 200 + Set-Cookie ritmo_session<br/>(HttpOnly · SameSite=Lax · host-only · 30d)
    U->>P: GET /treinos (com cookie)
    P->>U: renderiza o painel
    Note over U,A: request autenticado com ≤15d restantes
    A->>D: expires_at = now + 30d (sliding renewal)
    A-->>U: resposta + cookie renovado
    Note over U,A: "Sair" no header
    U->>A: POST /api/auth/logout
    A->>D: DELETE da sessão (só o dispositivo atual)
    A-->>U: 204 + cookie removido
```

Três camadas de proteção, uma autoridade: o `proxy.ts` otimista (redirect
de UX antes de render), o `apiFetch` do client (401 em uso →
`/login?next=`) e o `require_session` do backend — **a única que decide**.

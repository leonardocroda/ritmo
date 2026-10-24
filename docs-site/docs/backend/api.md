# Backend — API (referência)

19 endpoints sob `/api`. Autenticação por cookie de sessão
(`ritmo_session`) exceto os 3 públicos. O Swagger interativo do FastAPI
fica em [`/docs`](http://localhost:8000/docs) (local) e
[`https://ritmo-backend.onrender.com/docs`](https://ritmo-backend.onrender.com/docs)
(produção) — esta página é a referência legível com contexto;
contratos de payload seguem o princípio AD-009: **cada endpoint espelha
exatamente o que o painel correspondente renderiza**.

Módulos que não declaram query params ignoram quaisquer query strings não
declaradas (ex.: `?days=` em `GET /api/potential` não faz nada — CLR-04).

## Health check

| Método | Path | Auth | Descrição | Respostas |
|---|---|---|---|---|
| GET | `/api/health` | :material-lock-open-variant: pública | Liveness — **não toca o banco** (pingá-lo não gasta CU-horas do Neon) | `200 {"status":"ok","app":"Ritmo API","env":…}` |

## Auth (`app/auth/router.py`)

| Método | Path | Auth | Descrição | Respostas |
|---|---|---|---|---|
| POST | `/api/auth/register` | :material-lock-open-variant: pública | Cadastro por convite (`INVITE_CODE`, comparação constant-time); sucesso = **auto-login** | `201` + cookie · `403` convite vazio/inválido · `409` email duplicado · `422` campos |
| POST | `/api/auth/login` | :material-lock-open-variant: pública | Login email+senha | `200` + cookie · `401` genérico (nunca revela o campo) · `429` após 5 falhas/15min no email |
| POST | `/api/auth/logout` | :material-lock: sessão | Revoga **só a sessão do dispositivo** (celular e PC coexistem) | `204` |
| GET | `/api/auth/me` | :material-lock: sessão | Identidade do usuário logado | `200 {id, display_name}` · `401` |

## Sync Garmin (`app/garmin/router.py`)

| Método | Path | Auth | Descrição | Respostas |
|---|---|---|---|---|
| POST | `/api/sync` | :material-lock: sessão | Dispara o job de sync (backfill ou incremental); execução em `BackgroundTasks` | `201 {job_id}` · `409` já existe job ativo (lock 1/user) |
| GET | `/api/sync/jobs/latest` | :material-lock: sessão | Último job do usuário — é o que o botão polla a cada 2s | `200 {status, stats…}` |
| GET | `/api/sync/jobs/{job_id}` | :material-lock: sessão | Job específico | `200` · `404` (inexistente ou de outro usuário) |

O payload do job carrega `status` (`pending → running → done | error`),
`stats_json` (contadores por fase + warnings) e, em erro, o motivo —
incluindo `reauth_needed: true` quando o token expirou.

## Atividades (`app/activities/router.py`)

| Método | Path | Auth | Descrição | Query params | Respostas |
|---|---|---|---|---|---|
| GET | `/api/activities` | :material-lock: sessão | Lista paginada, da mais recente | `activity_type` = `running` (default) \| `all` · `limit` 1–100 (default 30) · `offset` ≥ 0 (default 0) | `200` |
| GET | `/api/activities/{activity_id}` | :material-lock: sessão | Detalhe com splits classificados por zona VDOT, tipo inferido, consistência e contexto do dia | — | `200` · `404` |

## Avaliação com IA (`app/evaluation/router.py`)

O router de avaliação **compartilha o prefixo** `/api/activities` — os
endpoints penduram no path do treino.

| Método | Path | Auth | Descrição | Respostas |
|---|---|---|---|---|
| POST | `/api/activities/{id}/evaluate` | :material-lock: sessão | Grava linha `pending` com o payload determinístico e responde na hora; a NIM roda em background | `201 {evaluation_id}` · `503` sem `NVIDIA_API_KEY` · `422` não é corrida · `404` |
| GET | `/api/activities/{id}/evaluate/{evaluation_id}` | :material-lock: sessão | Status para o polling (~2s) até `done`\|`error` | `200 {status, verdict…}` · `404` |

## Painéis (`potential/`, `health/`, `home/`, `profile/`)

| Método | Path | Auth | Descrição | Query params | Respostas |
|---|---|---|---|---|---|
| GET | `/api/potential` | :material-lock: sessão | Painel Performance: `{vdot, predictions, vo2max, decay, pmc}` — PMC com janela fixa de 60d (AD-017) | *(qualquer query é ignorada)* | `200` · `500` se a calibração VDOT estiver inválida |
| GET | `/api/health/summary` | :material-lock: sessão | Painel Saúde em blocos; série vazia vem `null` (estado vazio honesto) | `days` 7–365 (default 60) | `200` · `422` fora do intervalo |
| GET | `/api/home/today` | :material-lock: sessão | Painel Home: veredito do dia (V1–V6), chips de sinal, strip de carga, recomendações, digests P2 | — | `200` |
| GET | `/api/profile/hr-zones` | :material-lock: sessão | Valores de FC vigentes + config de zonas + zonas em bpm | — | `200` |
| PUT | `/api/profile/hr-zones` | :material-lock: sessão | Salva métricas (`fcmax`/`fcrest`/`fclthr`) e/ou config (`method` + `bounds`) — linhas effective-dated novas; idempotente para valor igual | — | `200` (o estado inteiro) · `422` apontando o campo/zona exata |
| GET | `/api/profile/hr-zones/history` | :material-lock: sessão | Timeline fundida de métricas + configs, mais recente primeiro | — | `200` |
| GET | `/api/profile/garmin-connection` | :material-lock: sessão | Estado da conexão: `connected` \| `reauth_needed` \| `not_connected` + metadados (só exibição) | — | `200` |

## Contrato de erro

| Código | Quando | Corpo |
|---|---|---|
| `401` | sem sessão / cookie expirado | JSON curto — o client redireciona `/login?next=<rota>` |
| `403` | registro com convite vazio/inválido | mensagem orientando o operador |
| `404` | recurso inexistente **ou de outro usuário** (user-scope não revela existência alheia) | — |
| `409` | conflito (email duplicado, job de sync ativo) | — |
| `422` | validação — sempre **PT-BR, campo a campo** (PUT de zonas aponta a zona exata) | `{detail: [{loc, msg}]}` |
| `429` | rate limit do login (5 falhas/15min por email) | genérico |
| `503` | `NVIDIA_API_KEY` ausente (botão Avaliar) | nada é criado |
| `500` | calibração VDOT inválida no `/api/potential` (estado de dados, não bug) | — |

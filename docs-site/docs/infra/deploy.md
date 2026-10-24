# Infra & Deploy — Produção

Produção com **US$ 0/mês e sem cartão** nas três plataformas,
dimensionada para o uso do MVP (≤5 pessoas, dados guardados por tempo
indefinido) — e o site de documentação junto, no mesmo Blueprint.

| Peça | Plataforma | Plano | Endereço |
|---|---|---|---|
| Frontend (Next.js) | Vercel | Hobby | `https://ritmo.vercel.app` |
| Backend (FastAPI) | Render | Free (Docker) | `https://ritmo-backend.onrender.com` |
| Postgres | Neon | Free | interno — só a connection string |
| Esta documentação | Render (static) | Free | `https://ritmo-docs.onrender.com` |

## Topologia

```mermaid
flowchart TB
    User["🧑 Corredor"]

    subgraph prod["Produção — US$ 0/mês, tudo em North Virginia"]
        Vercel["Vercel — Hobby<br/>ritmo.vercel.app<br/>CDN global, não dorme"]
        Render["Render — Free<br/>ritmo-backend.onrender.com<br/>Dorme 15 min → acorda ~1 min"]
        Docs["Render — static<br/>ritmo-docs.onrender.com<br/>não dorme"]
        Neon["Neon — Free<br/>Postgres aws-us-east-1<br/>Hiberna 5 min → acorda <1s"]
    end

    Garmin["Garmin Connect"]
    NIM["NVIDIA NIM"]

    User -- HTTPS --> Vercel
    Vercel -- "rewrite same-origin /api/*" --> Render
    Render -- "DATABASE_URL pooled + TLS" --> Neon
    Render -- "sync ~1 chamada/s" --> Garmin
    Render -- "avaliação IA (420s max)" --> NIM
    User -- "documentação" --> Docs
```

## Por que essas três (pesquisa out/2026)

- **Neon**, e não Render Postgres/Supabase: o Postgres free do Render
  **expira 30 dias após a criação** (deletado após 14 de carência); o
  Supabase pausa o projeto após 7 dias sem uso com restore **manual**.
  O Neon não expira e não pausa: a compute hiberna após 5 min sem
  queries e **acorda sozinha** (<1 s na primeira query). Free:
  1 GB/projeto, 100 CU-horas/mês.
- **Render**, e não serverless (Vercel Functions/Workers): o sync roda
  dezenas de minutos (chamadas sequenciais ~1/s) e a NIM até 420 s —
  serverless corta tudo em ≤300 s. O Render aceita até **100 min** por
  request e roda o mesmo Dockerfile do compose local (paridade de
  artefato). Free: 750 h/mês, 512 MB RAM, dorme após 15 min sem tráfego.
- **Vercel** porque o Next.js é deles: build por push, previews de PR,
  100 GB de transfer. Hobby = pessoal/não-comercial — ok para o Ritmo.
- **Regiões**: o link mais chatty é backend↔banco — toda a cadeia em
  North Virginia (Render `virginia`, Neon `aws-us-east-1`, funções
  `iad1`). O Neon TEM São Paulo, mas o Render não tem região BR: banco
  aqui pagaria ~200 ms de ida-e-volta por query até a Virgínia.
- **Esta doc**: static site no mesmo Blueprint do backend — build com
  o `python3-pip` do ambiente nativo, publish de `site/`, sem env vars.

## Setup (uma vez por conta)

### 1. Neon — o banco

1. <https://neon.com> → Sign up com GitHub → **Create project** na
   região **AWS us-east-1 (N. Virginia)**.
2. Copie a connection string **pooled** (host com `-pooler`) e troque o
   scheme para o driver do projeto:

```text
postgresql+psycopg://user:pass@ep-xxxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
```

Por que a pooled: o PgBouncer do Neon (modo transaction) aceita até 10k
conexões; o ajuste que o modo exige já está no engine
(`pool_pre_ping` + `prepare_threshold=None`).

### 2. Render — o backend (e a doc)

1. <https://render.com> → Get Started com GitHub → **New → Blueprint**
   → selecione o repo. O `render.yaml` sobe os dois serviços:
   `ritmo-backend` (Docker, `rootDir: backend`) e `ritmo-docs`
   (static, `rootDir: docs-site`).
2. O painel pede os 4 segredos do backend (`sync: false`):
   `DATABASE_URL` (string do passo 1) · `TOKEN_ENCRYPTION_KEY` (Fernet —
   sem ela o boot morre no fail-fast, GTDB-14) · `NVIDIA_API_KEY` ·
   `INVITE_CODE` (vazio = registro fechado).
3. Apply → primeiro build 2–3 min. Smoke:

```bash
curl https://ritmo-backend.onrender.com/api/health
# {"status":"ok","app":"Ritmo API","env":"prod"}
```

O `init_db()` do primeiro boot cria o schema no Neon e semeia o usuário
default — a cada cold start ele roda de novo (idempotente).

### 3. Vercel — o frontend

1. Importe o repo: preset Next.js detectado, **Root Directory
   `frontend`**, build padrão.
2. Env var `BACKEND_URL = https://ritmo-backend.onrender.com` (marque
   Production **e** Preview).
3. **O `BACKEND_URL` é resolvido NO BUILD** — trocou? Deployments → ⋯ →
   Redeploy. Se o subdomínio final não for `ritmo.vercel.app`, ajuste o
   `CORS_ORIGINS` no Render.

### 4. Bootstrap e primeiro uso

1. `uv run python -m app.auth.set_password` no seu terminal com o
   `DATABASE_URL` da sessão apontando pro Neon (§
   [Operações](operacoes.md)).
2. Login em `https://ritmo.vercel.app/login`.
3. Conecte o Garmin: `uv run python -m app.garmin.login --user <email>`
   (mesma sessão de env) → botão **Puxar do Garmin** no `/perfil`. O
   backfill de 180d roda num request só (~10 min) — o Render aguenta,
   só não feche a aba.
4. Convidados: preencha `INVITE_CODE` no Render e compartilhe
   `/registrar` + o código.

## Cold starts (o preço do free)

| Serviço | Dorme quando | Acorda em |
|---|---|---|
| Render (backend) | 15 min sem tráfego | ~1 min na primeira request — a segunda funciona |
| Neon (banco) | 5 min sem queries | <1 s, transparente |
| Vercel / docs | não dormem | — |

O `/api/health` **não toca o banco** de propósito. **Nunca aponte um
pinger para endpoints que usem o banco**: manter o Neon acordado 24/7
custa ~186 CU-horas/mês (quase o dobro das 100 gratuitas). Uso real de
≤5 pessoas sobra folga.

## Limites do free (out/2026) e upgrade

| Plataforma | Limite | Ao estourar |
|---|---|---|
| Neon | 1 GB · 100 CU-h/mês | writes falham (1 GB) · compute pausa até virar o mês |
| Render | 750 h/mês · 512 MB RAM · 5 GB banda · 500 min build | serviço suspenso até o mês virar |
| Vercel Hobby | 100 GB transfer · não-comercial | feature pausa ~30 dias |

Caminho quando doer: Render **Starter** $7/mês (não dorme), Neon
**Launch** pay-as-you-go, Vercel **Pro** $20/mês (só se virar comercial).

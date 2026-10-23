# Deploy — Vercel + Render + Neon (Fase 2.5)

Produção do Ritmo com **US$ 0/mês e sem cartão de crédito** nas três
plataformas, dimensionada para o uso do MVP (≤5 pessoas, dados guardados
por tempo indeterminado):

| Peça | Plataforma | Plano | Endereço |
|---|---|---|---|
| Frontend (Next.js) | Vercel | Hobby | `https://ritmo.vercel.app` |
| Backend (FastAPI) | Render | Free | `https://ritmo-backend.onrender.com` |
| Postgres | Neon | Free | interno — só a connection string |

```
navegador → ritmo.vercel.app          (Vercel — CDN global, não dorme)
              │  rewrite same-origin /api/* (next.config.ts, AD-020)
              ▼
          ritmo-backend.onrender.com   (Render — Docker, Virginia)
              │  DATABASE_URL (string pooled, TLS)
              ▼
          Neon Postgres               (aws-us-east-1 — North Virginia)
```

O frontend segue chamando `/api/*` **relativo** (`API_BASE = ""`): na
produção o rewrite aponta para a URL pública do Render (`BACKEND_URL`).
O cookie de sessão continua host-only do domínio que o usuário abriu,
agora com HTTPS ponta a ponta (`SESSION_COOKIE_SECURE=true`).

## Por que essas três (pesquisa out/2026)

- **Neon**, e não Render Postgres/Supabase: o Postgres free do Render
  **expira 30 dias após a criação** (deletado após 14 de carência); o
  Supabase free pausa o projeto após 7 dias sem uso e o restore é
  **manual** no dashboard. O Neon não expira e não pausa por inatividade:
  a compute hiberna após 5 min sem queries e **acorda sozinha** (<1 s na
  primeira query). Free: 1 GB/projeto, 100 CU-horas de compute/mês.
- **Render**, e não serverless (Vercel Functions/Cloudflare Workers): o
  backend faz syncs Garmin de dezenas de minutos (chamadas sequenciais a
  ~1/s) e chamadas NIM de até 420 s — serverless corta tudo em ≤300 s.
  O Render aceita requests de até **100 min** e roda o mesmo Dockerfile
  do compose local (paridade de artefato). Free: 750 h/mês, 512 MB RAM.
  Dorme após 15 min sem tráfego (acorda em ~1 min).
- **Vercel** porque o Next.js é deles: build automático por push,
  previews de PR, 100 GB de transfer/mês. O plano Hobby é
  **pessoal/não-comercial** — ok para o Ritmo (uso próprio, sem cobrança).
- **Regiões**: o link mais chattty é backend↔banco, então toda a cadeia
  fica em North Virginia — Render `virginia`, Neon `aws-us-east-1`,
  funções da Vercel no default `iad1`. O Neon TEM São Paulo
  (`aws-sa-east-1`), mas o Render não tem região no BR: banco aqui
  pagaria ~200 ms de ida-e-volta por query até a Virgínia. Do Brasil,
  só o primeiro hop (navegador→Vercel) cruza o continente.

## 1. Neon — criar o banco

1. <https://neon.com> → **Sign up with GitHub** (sem cartão).
2. **Create project** → região **AWS us-east-1 (N. Virginia)**.
3. Copie a connection string **pooled** — o host contém `-pooler`:

   ```
   postgresql://user:pass@ep-xxxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```

4. Ajuste o **scheme** para o driver do projeto (psycopg3, AD-007) — esse
   é o valor da `DATABASE_URL` no Render:

   ```
   postgresql+psycopg://user:pass@ep-xxxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```

Por que a pooled: o PgBouncer do Neon (modo transaction) aceita até 10k
conexões — cobre cold starts e deploys concorrentes sem susto com o
pool do SQLAlchemy (5 + overflow 10). O ajuste que o modo transaction
exige já está no engine (`pool_pre_ping` + `prepare_threshold=None` em
`backend/app/db/engine.py`).

## 2. Render — publicar o backend

1. <https://render.com> → **Get Started** com GitHub.
2. **New → Blueprint** → selecione o repo do Ritmo. O Render lê o
   `render.yaml` da raiz: web service Docker, `rootDir: backend`, plano
   free, região virginia, health check em `/api/health`.
3. O painel pede os 4 segredos (`sync: false` no blueprint):
   - `DATABASE_URL` — a string do passo 1 (com `+psycopg`);
   - `TOKEN_ENCRYPTION_KEY` — gere uma Fernet:
     `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`;
   - `NVIDIA_API_KEY` — a chave do build.nvidia.com;
   - `INVITE_CODE` — pode deixar vazio (registro fechado).
4. **Apply** → primeiro build (Docker + `uv sync`, 2–3 min). Faltando
   `TOKEN_ENCRYPTION_KEY` ou `DATABASE_URL`, o boot morre no fail-fast,
   o health check não passa e o deploy aparece como falho (GTDB-14) —
   é o comportamento esperado.
5. Smoke test:

   ```bash
   curl https://ritmo-backend.onrender.com/api/health
   # {"status":"ok","app":"Ritmo API","env":"prod"}
   ```

No primeiro boot o `init_db()` cria o schema no Neon e semeia o usuário
default — a mesma sequência do compose local, zero passo extra. A cada
cold start ele roda de novo (idempotente por design).

### CLIs: na sua máquina, não no Render (o Shell é pago)

O bootstrap de senha e o re-login Garmin (decisão travada: re-auth é CLI)
**não precisam rodar no Render** — as CLIs só precisam alcançar o banco, e
o Neon é público: a connection string vale de qualquer máquina. Rode no
seu terminal de sempre, em `backend/`, apontando o `DATABASE_URL`
**da sessão** para a produção:

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://user:pass@ep-xxxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

uv run python -m app.auth.set_password             # bootstrap/reset do dono
uv run python -m app.garmin.login --user <email>   # login Garmin — MFA no terminal
```

Regras do fluxo:

- A env vive **só na sessão do PowerShell** — fechou o terminal, volta ao
  `.env` local; os ambientes nunca se misturam em arquivo.
- **Pré-requisito**: o backend precisa ter bootado ao menos uma vez — o
  `init_db()` do primeiro deploy cria as tabelas no Neon (a CLI não cria).
- **Fernet**: o login Garmin cifras o token na SUA máquina e o backend
  decifra no Render — a `TOKEN_ENCRYPTION_KEY` local tem que ser a
  **mesma** do Render. Senha de login não usa Fernet (argon2), então o
  `set_password` funciona com qualquer chave.
- Validado ponta a ponta (out/2026): env da sessão + `set_password` numa
  base recém-criada → seed id=1 vinculado ao email com hash argon2.

## 3. Vercel — publicar o frontend

1. <https://vercel.com> → **Continue with GitHub**.
2. **Add New → Project** → importe o repo do Ritmo.
3. Configuração:
   - **Framework Preset**: Next.js (detectado sozinho);
   - **Root Directory**: `frontend`;
   - Build Command / Output: padrão (`next build`).
4. **Environment Variables** (marque Production **e** Preview):
   - `BACKEND_URL` = `https://ritmo-backend.onrender.com`
5. **Deploy**.

> **O `BACKEND_URL` é resolvido NO BUILD**: o Next materializa as rewrites
> no build output (AD-020). Trocou a env? **Redeploy** (Deployments → ⋯ →
> Redeploy) para o novo destino valer.

O subdomínio final é `https://<nome-do-projeto>.vercel.app`. Se não for
`ritmo.vercel.app`, atualize o `CORS_ORIGINS` no Render (Settings →
Environment) — sobra de segurança para acesso browser direto à API; o
fluxo normal nem passa por CORS, é same-origin.

## 4. Bootstrap e primeiro uso

1. No seu terminal (§ *CLIs: na sua máquina*): `uv run python -m
   app.auth.set_password` — vincula email+senha ao usuário seed (o
   "Leonardo" criado pelo `init_db`).
2. Entre em `https://ritmo.vercel.app/login`.
3. Conecte o Garmin: `uv run python -m app.garmin.login --user <email>`
   com o `DATABASE_URL` da sessão apontando pro Neon (tokens cifrados no
   banco com a `TOKEN_ENCRYPTION_KEY`) → botão **Puxar do Garmin** no
   `/perfil`. O backfill de 180d roda inteiro num request só (~10 min) —
   o Render aguenta (timeout de 100 min), só não feche a aba.
4. Convidados: preencha `INVITE_CODE` no Render e compartilhe
   `https://ritmo.vercel.app/registrar` + o código.

## Cold starts (o preço do free)

| Serviço | Dorme quando | Acorda em |
|---|---|---|
| Render (backend) | 15 min sem tráfego | ~1 min na primeira request |
| Neon (banco) | 5 min sem queries | <1 s, transparente |
| Vercel (frontend) | não dorme | — |

- O health check `/api/health` **não toca o banco** de propósito: pingá-lo
  não gasta CU-horas do Neon.
- **Nunca aponte um pinger para endpoints que usem o banco**: manter o
  Neon acordado 24/7 custa ~186 CU-horas/mês (quase o dobro das 100
  gratuitas) — estourou, a compute só volta no mês seguinte (dados a
  salvo). Uso real de ≤5 pessoas fica com folga enorme.
- Se o ~1 min do Render incomodar depois: cron-job.org (grátis) a cada
  10 min em `/api/health` resolve — decidimos deixar fora por ora.

## Limites do free tier (out/2026) e o que acontece ao estourar

| Plataforma | Limite | Ao estourar |
|---|---|---|
| Neon | 1 GB/projeto · 100 CU-horas/mês | writes falham (1 GB) · compute pausa até virar o mês |
| Render | 750 h/mês · 512 MB RAM · 5 GB banda · 500 min build | serviço suspenso até virar o mês · sem cobrança |
| Vercel Hobby | 100 GB transfer · 1M req CDN · não-comercial | feature pausa ~30 dias · sem cobrança |

Caminho de upgrade quando doer: Render **Starter** $7/mês (não dorme
mais), Neon **Launch** pay-as-you-go (sem mensalidade mínima), Vercel
**Pro** $20/mês (só se um dia virar comercial).

## Backups

- Neon free guarda **1 snapshot manual** (Dashboard → projeto →
  *Backups* → Create snapshot) — renove após migrações grandes.
- Dump completo sob demanda (use a string **sem** `-pooler` — a direta;
  requer IPv6, o normal em casa):

  ```bash
  pg_dump "<connection string direta>" -F c -f ritmo-$(date +%F).dump
  ```

- O Postgres do compose local continua sendo a instância de dev.

## Operações do dia a dia

- **Deploy novo**: push na `main`. Auto-deploy nos dois: o Render só
  rebuilda se houve mudança em `backend/` (`rootDir`), a Vercel se houve
  em `frontend/` (Root Directory) — mudança de docs não gera build.
- **Migrations**: não há Alembic — `init_db()` no boot cria o que faltar
  (`create_all` + emendas idempotentes). Deploy = migration.
- **Logs**: Render (service → *Events/Logs*); Vercel (Deployments →
  *Runtime Logs* — o Hobby mantém 1 h).
- **Env vars**: mudou segredo no Render → Settings → Environment → Save
  (redeploy automático). Na Vercel idem, mas lembre do redeploy manual
  quando for `BACKEND_URL`.

## Troubleshooting rápido

| Sintoma | Causa provável |
|---|---|
| Deploy Render falha no health check | `TOKEN_ENCRYPTION_KEY` ausente (fail-fast GTDB-14) ou `DATABASE_URL` errada |
| `prepared statement "..." already exists` | string Neon **sem** `-pooler` — use a pooled (o engine já desliga o prepare) |
| 502 após período de silêncio | cold start do Render — a segunda tentativa funciona |
| Login volta pro `/login` em loop | `SESSION_COOKIE_SECURE` requer HTTPS — no local ele é `false` |
| 403 no `/registrar` | `INVITE_CODE` vazio = registro fechado (comportamento esperado) |
| Frontend no ar, API 404 | `BACKEND_URL` definida DEPOIS do build — redeploy na Vercel |
| CLI: `relation "users" does not exist` | backend nunca bootou no Neon — faça o deploy primeiro (init_db cria as tabelas) |
| Sync dá `reauth_needed` logo após o login da sua máquina | `TOKEN_ENCRYPTION_KEY` local ≠ a do Render — o token foi cifrado com outra chave |
| Primeiro clique lento (~1 min) | backend acordando — os próximos são instantâneos |

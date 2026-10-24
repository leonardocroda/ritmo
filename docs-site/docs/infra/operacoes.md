# Infra — Operações & Troubleshooting

O dia a dia de manter o Ritmo no ar: deploys, CLIs de operação, backups
e a tabela de sintomas.

## Deploys

- **Deploy novo = push na `main`** (auto-deploy nos dois lados). O Render
  só rebuilda o backend se houve mudança em `backend/` (`rootDir`) e a
  doc se houve em `docs-site/`; a Vercel rebuilda o frontend se houve
  em `frontend/` — mudança de docs não gera build de app.
- **Migrations**: não há Alembic — o `init_db()` de cada boot cria o que
  faltar (`create_all` + emendas idempotentes, AD-019). Deploy =
  migration.
- **Env vars**: segredo mudou no Render → Settings → Environment → Save
  (redeploy automático). Na Vercel idem — mas `BACKEND_URL` exige
  **redeploy manual** (resolvida no build).
- **Logs**: Render (*Events/Logs*) · Vercel (*Deployments → Runtime
  Logs*, 1 h no Hobby).

## CLIs de operação — na SUA máquina, não no Render

O Shell do Render é pago — e desnecessário: o Neon é público, a
connection string vale de qualquer máquina. As CLIs só precisam alcançar
o banco. Em `backend/`, aponte a env **apenas para a sessão do
PowerShell** (fechou o terminal, volta ao `.env` local — os ambientes
nunca se misturam em arquivo):

```powershell
cd backend
$env:DATABASE_URL = "postgresql+psycopg://user:pass@ep-xxxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

uv run python -m app.auth.set_password             # bootstrap/reset do dono
uv run python -m app.garmin.login --user <email>   # login/renovação Garmin — MFA no terminal
```

Regras do fluxo:

- **Pré-requisito**: o backend precisa ter bootado ao menos uma vez — o
  `init_db()` do primeiro deploy cria as tabelas (a CLI não cria).
- **Fernet**: o login Garmin cifra o token na SUA máquina e o backend
  decifra no Render — a `TOKEN_ENCRYPTION_KEY` local tem que ser a
  **mesma** do Render. Senha não usa Fernet (argon2), então o
  `set_password` funciona com qualquer chave.
- Re-login Garmin substitui os tokens do usuário; `import_tokens` (o
  legado run-once do tokenstore de arquivo) recusa se o usuário 1 já
  tem tokens.

## Backups

- **Neon free guarda 1 snapshot manual** (Dashboard → projeto →
  *Backups* → Create snapshot) — renove após migrações grandes.
- Dump completo sob demanda — use a string **sem** `-pooler` (a direta;
  requer IPv6, o normal em casa):

```bash
pg_dump "<connection string direta>" -F c -f ritmo-$(date +%F).dump
```

- O Postgres do compose local segue sendo a instância de dev.

## Troubleshooting

| Sintoma | Causa provável |
|---|---|
| Deploy Render falha no health check | `TOKEN_ENCRYPTION_KEY` ausente (fail-fast GTDB-14) ou `DATABASE_URL` errada |
| `prepared statement "..." already exists` | string Neon **sem** `-pooler` — use a pooled (o engine já desliga o prepare) |
| 502 após período de silêncio | cold start do Render — a segunda tentativa funciona |
| Login volta pro `/login` em loop | `SESSION_COOKIE_SECURE` requer HTTPS — no local é `false` |
| 403 no `/registrar` | `INVITE_CODE` vazio = registro fechado (comportamento esperado) |
| Frontend no ar, API 404 | `BACKEND_URL` definida DEPOIS do build — redeploy na Vercel |
| CLI: `relation "users" does not exist` | backend nunca bootou no Neon — faça o deploy primeiro |
| Sync dá `reauth_needed` logo após o login local | `TOKEN_ENCRYPTION_KEY` local ≠ a do Render — token cifrado com outra chave |
| Primeiro clique lento (~1 min) | backend acordando — os próximos são instantâneos |
| Doc não atualizou | Blueprint novo serviço exige **Sync** no dashboard; depois, push em `docs-site/` |

## Segredos — quem vive onde

| Segredo | Onde | Nota |
|---|---|---|
| `DATABASE_URL` (Neon) | Render (painel) + sessão PowerShell das CLIs | nunca em arquivo no repo |
| `TOKEN_ENCRYPTION_KEY` | Render + `.env` local (compose) | **idêntica nos dois** — é ela que cifra/decifra os tokens Garmin |
| `NVIDIA_API_KEY` | Render + `.env` local | sem ela, Avaliar responde 503 |
| `INVITE_CODE` | Render | vazio = registro fechado |
| `BACKEND_URL` | Vercel (build) + compose (build arg) | resolvida no build — redeploy ao trocar |
| Senha Garmin | **nunca** no site | re-auth é CLI (AD-014) |

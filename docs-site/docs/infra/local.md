# Infra — Ambiente Local

Stack local por `docker-compose.yml` (AD-007): **os mesmos artefatos da
produção** — o Dockerfile do backend e o build standalone do Next.

## Stack completo (recomendado)

```bash
docker compose up -d          # postgres + backend :8000 + frontend :3000
curl http://localhost:8000/api/health
```

| Serviço | O que é | Porta |
|---|---|---|
| `postgres` | `postgres:16` com healthcheck; init script cria os bancos `ritmo` e `ritmo_test` na primeira inicialização do volume | 5432 |
| `backend` | Dockerfile do backend; `DATABASE_URL` aponta para o hostname `postgres` | 8000 |
| `frontend` | Dockerfile multi-stage (standalone); `BACKEND_URL=http://backend:8000` como **build arg** | 3000 |

Pré-requisito: Docker. No primeiro `up` a imagem `postgres:16` é baixada
(mais lenta); depois fica cacheada. O `.env` do backend é opcional no
compose — presente, as vars fluem para o container; conflito perde para
o `environment:` do compose.

## Dev diário (hot-reload fora do compose)

```bash
docker compose up -d postgres   # só o banco
cd backend
cp .env.example .env            # DATABASE_URL → localhost:5432
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs

cd ../frontend
npm install
npm run dev                     # http://localhost:3000
```

No `npm run dev` o `BACKEND_URL` cai no fallback `http://localhost:8000`.

## Testes (backend)

```bash
docker compose up -d postgres   # obrigatório: a suite roda no banco ritmo_test
cd backend
uv run pytest
```

Sem o Postgres de pé a suíte falha imediatamente instruindo subir o
banco — **nenhum teste roda em SQLite**. Detalhes em
[Testes](../backend/testes.md).

## Porta 5432 ocupada no host?

Sobrescreva o binding com um `docker-compose.override.yml`:

```yaml
services:
  postgres:
    ports:
      - "5433:5432"
```

Dentro do compose nada muda (o backend usa o hostname `postgres`); só o
`DATABASE_URL` do `.env` passa a apontar `localhost:5433`.

## Acessando pela LAN (celular etc.)

O frontend chama a API **pelo próprio Next** (rewrite same-origin,
AD-020): o cookie de sessão vale para o host que você abriu —
`localhost:3000` e `http://<IP-da-LAN>:3000` funcionam igual. Mudou o
IP do PC (DHCP)? Nada muda, sem rebuild (o `BACKEND_URL` do compose é o
hostname interno `backend`, não o IP externo).

## Documentação local (este site)

```bash
cd docs-site
uv run mkdocs serve --dev-addr localhost:8001   # hot-reload em :8001
```

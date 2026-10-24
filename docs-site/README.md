# docs-site — Documentação técnica do Ritmo

Site de documentação em **MkDocs Material** com diagramas **Mermaid**.
Publica em `https://ritmo-docs.onrender.com` pelo mesmo Blueprint do backend.

## Rodando local

```bash
uv run mkdocs serve --dev-addr localhost:8001   # → http://localhost:8001
```

A porta 8001 evita colidir com o backend dev (:8000). Na primeira execução
o `uv run` resolve o ambiente sozinho (`uv sync` implícito).

## Build de verificação (gate antes de commit)

```bash
uv run mkdocs build --strict
```

`--strict` transforma link quebrado e entrada de `nav:` apontando para
arquivo inexistente em **erro** de build. O site estático sai em `site/`
(ignorado pelo git).

## Publicação

O deploy é o serviço `ritmo-docs` do `render.yaml` na raiz do monorepo:

| | |
|---|---|
| Tipo | `runtime: static` (static site — free, não dorme) |
| Fonte | `rootDir: docs-site`, branch `main` |
| Build | `pip install "mkdocs-material>=9.5" && mkdocs build` (python3-pip do build image nativo do Render) |
| Publish | `staticPublishPath: site` |
| Endereço | `https://ritmo-docs.onrender.com` |

Um push na `main` com mudanças em `docs-site/` gera deploy automático.
**Primeiro deploy**: no dashboard do Render, *Blueprint → Sync* detecta o
serviço novo — nenhum segredo é pedido (a doc é pública, sem env vars).

> **Nota de manutenção (out/2026)**: o Material for MkDocs entra em fim de
> vida em maio/2027; o sucessor mantido pela mesma equipe é o
> [Zensical](https://zensical.org), que lê este `mkdocs.yml` nativamente
> (mesma config de Mermaid) — a migração futura é trocar o comando
> `mkdocs` por `zensical`.

## Estrutura

```
docs-site/
├── mkdocs.yml        # tema, extensões (mermaid) e nav
├── pyproject.toml    # única dependência: mkdocs-material (via uv)
└── docs/
    ├── index.md            # Início — visão geral + mapa da doc
    ├── arquitetura/        # contexto, containers, fluxos, decisões AD-NNN
    ├── backend/            # API, banco, sync Garmin, auth, IA, cálculo, config, testes
    ├── frontend/           # rotas, componentes, páginas, padrões
    ├── infra/              # produção, ambiente local, operações
    └── produto/            # plano da plataforma
```

## Como adicionar uma página

1. Crie `docs/<secao>/<pagina>.md`.
2. Adicione a entrada em `nav:` no `mkdocs.yml` — a `nav:` cresce junto com
   as fases (entrada sem arquivo quebra o `--strict`).
3. Diagramas: bloco de código ` ```mermaid ` — `flowchart`, `sequenceDiagram`,
   `erDiagram` e `stateDiagram-v2` são os tipos em uso.
4. Rode `uv run mkdocs build --strict` antes do commit.

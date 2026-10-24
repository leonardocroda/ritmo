# Frontend — Arquitetura das Páginas

Fluxo de dados, endpoints consumidos e estados de cada página. Padrão
comum (DSN-23): **loading = skeleton no formato da composição** (nunca
spinner), **erro = card com a mensagem do contrato**, **vazio = honesto
e orientado ao primeiro sync**, bloco sem dado é **omitido** (nunca
"—" fora de tabela). Controle de race: `useRef` de sequência ou flag
`cancelled`.

## `/` — Home

- **Fetch**: 1 round-trip `GET /api/home/today` no mount. Sem polling.
- **Estados**: `loading` → skeletons (herói + chips) · `error` → card ·
  `empty` (sem veredito + sem último treino + strip zerada) → orienta o
  primeiro sync com link para `/perfil` (sem botão de sync aqui — ele
  mora no Perfil, AD-023) · `ready` → veredito → chips → recomendações
  → digests P2 (omitidos quando `null`).
- A Home **roteia** — nunca duplica painel: chips levam a
  `/treinos/{id}` e `/performance`.

## `/treinos` — lista

- **Fetch**: `GET /api/activities?activity_type={running|all}&limit=30&offset=…`
- "Carregar mais" anexa página deduplicando ids; troca de filtro reseta
  a paginação; `requestSeq` descarta resposta velha.
- Estados: skeletons de cartão · erro com mensagem · vazio orientando o
  sync · itens com badge "Avaliado".

## `/treinos/[id]` — detalhe

- **Server**: `<Suspense>` com skeleton → `await params` → `id` numérico
  (`/^\d+$/`) senão `notFound()` → `<WorkoutDetail key={id}>`
  (remontagem por treino).
- **Fetch (client)**: `GET /api/activities/{id}`.
- **Polling**: enquanto houver avaliação `pending`, `setInterval` de 2s
  no `GET .../evaluate/{evaluationId}` de cada pendente — o card
  "Analisando treino…" vira o veredito; badge "Avaliado" acende no done.
- **Composição**: header (data, nome, badges tipo/avaliado) → métricas →
  Estrutura → Contexto do dia (chips: só o que existir) → Consistência
  (tabela; null se <8 km ou <4 voltas) → Avaliar com IA (form + card +
  histórico) → Voltas (`SplitsChart` ou nota honesta).

## `/saude` — painel Saúde

- **Fetch por janela**: `GET /api/health/summary?days={7|30|42|60|90}`
  — troca de janela **mantém** os dados na tela com "atualizando…"
  inline no filtro; erro de refetch não derruba o que já está
  renderizado; `requestSeq` anti-race.
- 4 seções numeradas (PanelSection): Sono → Recuperação → Dose-resposta
  → Equilíbrio de vida; `HrvChart`/`HrvTable` remontam por janela.
- Estado vazio geral (todos os blocos null) aponta o primeiro sync;
  bloco individual vazio tem seu próprio empty honesto.

## `/performance` — painel Performance

- **Fetch**: 1 round-trip `GET /api/potential` (PMC com janela fixa de
  60d — o `?days=` é ignorado por contrato).
- 4 blocos narrativos: Onde estou (GapCard + timeline) → O que isso
  prevê (predições 4 métodos + decay) → O que o relógio estima (VO2max —
  **seção omitida** quando não há dados) → Carga de treino (PMC).
- Estado vazio recalculado (timeline ≤1 ponto + vo2max null + decay
  vazio + pmc null) aponta o sync.

## `/perfil` — conexão + zonas de FC

- **Fetch**: `Promise.all([hr-zones, hr-zones/history, garmin-connection])`.
- **Escrita**: cada seção salva `PUT /api/profile/hr-zones` — **a
  resposta do PUT vira o estado** ("salvar → zonas mudam na hora") e o
  histórico re-busca com `historySeq` guard.
- 4 seções: Conexão Garmin (`ConnectionCard` + `SyncButton` — status e
  ação juntos, AD-023) · 1 Valores · 2 Método e zonas · 3 Histórico.
- 422 da API vira erro inline no campo exato (métrica ou zona).

## `/login` e `/registrar`

- **POST** `/api/auth/login` · `/api/auth/register`; sucesso →
  `router.replace(next ?? "/")`.
- Erros inline: login 401/429 PT-BR; registro 422 por campo + 403/409 no
  topo; 201 = auto-login.
- Boundary `<Suspense>` interna por `useSearchParams` (cacheComponents).

## `/site` — landing pública

- **Zero fetch**: server component estático, zero JS de cliente — só
  HTML/CSS com fontes e tokens; imagens `<img>` de `public/prints/`
  (prints da interface real com dados ilustrativos declarados na
  própria página).
- Visitante sem sessão acessa pela raiz `/` via **rewrite** do proxy —
  a URL nunca muda; CTAs levam a `/treinos` (fluxo de login de sempre).

## Endpoints consumidos pelo client (16)

```text
POST   /api/auth/register            POST  /api/auth/login
POST   /api/auth/logout              GET   /api/auth/me
POST   /api/sync                     GET   /api/sync/jobs/latest
GET    /api/activities               GET   /api/activities/{id}
POST   /api/activities/{id}/evaluate
GET    /api/activities/{id}/evaluate/{evaluationId}
GET    /api/potential                GET   /api/health/summary?days=
GET    /api/home/today               GET   /api/profile/hr-zones
PUT    /api/profile/hr-zones         GET   /api/profile/hr-zones/history
GET    /api/profile/garmin-connection
```

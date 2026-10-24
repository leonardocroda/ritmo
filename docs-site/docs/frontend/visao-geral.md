# Frontend — Visão Geral

Next.js 16 (App Router) · React 19 · Tailwind 4 · Recharts 3 — tema dark
v0.3, mobile-first, PT-BR. O frontend é **só apresentação + transporte**:
toda regra e todo número vêm prontos da API (contratos espelhados 1:1 em
`src/lib/api.ts`).

| Peça | Versão/uso |
|---|---|
| Next.js | **16.4.2** — App Router, `cacheComponents`, `partialPrefetching` |
| React | 19.3.1 |
| Tailwind | **4** — CSS-first: tokens via `@theme inline` no `globals.css`, **sem** `tailwind.config.js` |
| Recharts | 3.10 — todos os gráficos de série (menos o SVG próprio dos splits, AD-008) |
| Deps de runtime | apenas `next`, `react`, `react-dom`, `recharts` |

## Este NÃO é o Next.js que você conhece

O Next 16 mudou convenções que aparecem em todo o código — o
`frontend/AGENTS.md` avisa antes de qualquer edição:

| Convenção | O que muda |
|---|---|
| **`proxy.ts`** | o `middleware.ts` virou `src/proxy.ts`, exportando `proxy` (não `middleware`) |
| **`params` é Promise** | acesso síncrono removido — `/treinos/[id]` faz `await params` dentro de `<Suspense>` |
| **`cacheComponents`** | `usePathname`/`useSearchParams` suspendem no prerender → boundaries `<Suspense>` internas em Nav, login, registrar e `/treinos/[id]` |
| Tipos globais | `PageProps<"/treinos/[id]">`, `LayoutProps<"/">` |
| `output` | `standalone` **condicional**: `process.env.VERCEL ? undefined : "standalone"` — na Vercel usa o build nativo; no Docker/compose, `server.js` autocontido |

## Estrutura

```
frontend/
├── next.config.ts          # rewrites /api/* → BACKEND_URL (AD-020), standalone
├── src/
│   ├── proxy.ts            # decisões de rota por presença de cookie
│   ├── app/
│   │   ├── layout.tsx      # shell: fontes, metadata, themeColor
│   │   ├── globals.css     # tokens v0.3 + @theme inline + skeleton
│   │   ├── (app)/          # painéis com Header + TabBar (auth obrigatória)
│   │   ├── (auth)/         # login/registrar sem header
│   │   └── (site)/site/    # landing pública (server estático, zero JS)
│   ├── components/
│   │   ├── Header.tsx · Nav.tsx (Nav + TabBar) · UserMenu.tsx
│   │   ├── SyncButton.tsx · Skeleton.tsx · PanelSection.tsx
│   │   ├── home/ · workouts/ · health/ · performance/ · profile/
│   └── lib/
│       ├── api.ts          # cliente tipado — A UI lê exclusivamente daqui
│       ├── format.ts       # formatadores PT-BR (wall clock)
│       └── chartTheme.ts    # tokens de gráfico + tooltipCard/legendCaption
├── scripts/site/           # captura de prints + QA da landing
└── public/prints/          # PNGs da interface real (mock) usados no /site
```

## Camadas

- **Páginas server** (`page.tsx`) — shell mínimo: validação de rota,
  `<Suspense>`, montagem do painel client. `/perfil`, `/login` e
  `/registrar` são client pages.
- **Painéis client** (`components/<painel>/Panel.tsx`) — máquina de
  estados `loading → error | empty | ready`, fetch único ou por janela,
  composição dos cards.
- **`lib/api.ts`** — o **único** ponto de fetch: tipos espelho dos
  schemas do backend, `ApiError`/`AuthError`, redirect de 401. Nenhum
  componente chama `fetch` direto.
- **`lib/format.ts`** — PT-BR (vírgula decimal), datas **wall clock**
  (exibidas como gravadas, sem conversão de fuso).

Próximo: [rotas e navegação](rotas.md) ·
[catálogo de componentes](componentes.md).

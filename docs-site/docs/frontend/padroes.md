# Frontend — Padrões Transversais

## Cliente de API (`src/lib/api.ts`)

- **Base relativa** (`API_BASE = ""`): o rewrite same-origin (AD-020)
  entrega `/api/*` no próprio host — o cookie vale para qualquer
  host:porta que o usuário abriu.
- `apiFetch`: `credentials: "include"`, `cache: "no-store"` (dados do
  banco sempre frescos) e **401 fora de auth →
  `window.location.replace("/login?next=<path+query>")`** com guardas
  anti-loop (sessão expirou em uso).
- Erros canônicos: `ApiError` (status + mensagem) e `AuthError`
  (fieldErrors do 422 — alimenta os erros inline por campo).

## Identidade visual (v0.3, AD-022)

Tailwind 4 CSS-first — tokens em `globals.css` expostos por `@theme inline`
(`bg-card`, `text-muted`, `rounded-card`, `font-sans`…):

| Token | Valor | Uso |
|---|---|---|
| `--background` | `#0B0F12` (Night) | fundo |
| `--foreground` | `#A1AAA9`→`#F5F7F2` | texto / secundário (`--muted`) |
| `--accent` | `#B7F36B` (Lime) | acento funcional — **nunca fundo geral** |
| `--card` / `--raised` / `--deep` | `#121815` / `#1B241A` / `#273323` | superfícies (herói = Forest) |
| `--border` / `--border-hover` | `#354039` / `#4A574E` | decorativa / interativa |
| `--good` / `--attention` / `--alert` | lime / `#E9B44C` / `#EF6757` | semântica de saúde (sempre com texto) |

- Fontes: **Instrument Sans** (400–700, números tabulares) + Geist Mono;
  `themeColor #0B0F12`; `lang="pt-BR"`.
- **Sentence case** — caps só em eyebrows/labels; PT-BR com vírgula decimal.
- Skeletons: keyframe `skeleton-pulse` 1,6s, gradiente raised→deep.
- Cores das zonas VDOT vêm **do backend** (`ZoneMeta.color`) e ficam
  restritas a contexto de treino — lime da marca ≠ verde-easy de zona
  (regra de coexistência da AD-022).

## Gráficos

- Tema único por `chartTheme.ts`: **"contexto em neutro, um único
  destaque lime"**; tooltips custom (`tooltipCard`); legendas por método
  sempre visíveis (AD-009).
- Recharts para toda série temporal (AD-008); **exceção**: `SplitsChart`
  em SVG próprio — barras com **largura proporcional à duração da
  volta** (pausa de 30s ≠ tiro de 3 km), cor por zona VDOT, linha de FC,
  banda de relevo, pace clampado [180,420] s/km só no desenho.
- ViewBox calibrado no mobile 390px, escala para cima em telas maiores.

## Mobile-first

- `<768px`: **tab bar inferior fixa** (5 colunas, backdrop-blur,
  `safe-area-inset-bottom`, alvo ≥44px) + header só com wordmark+conta;
  o wrapper `(app)` reserva `pb-24`.
- `≥768px`: tab bar some, navegação vira top bar rolável no Header.
- UAT padrão: aprovação em 390px via LAN antes de fechar qualquer feature.

## Datas

**Wall clock**: exibidas como gravadas pelo Garmin, sem conversão de
fuso (premissa documentada em `format.ts`) — helpers locais
(`dateParts`/`epochDays`) evitam o bug UTC do `new Date(iso)`.

## Estados (DSN-23)

```text
loading → skeleton no formato da composição que vai chegar
error   → card com a mensagem do contrato do backend
empty   → honesto: orienta o primeiro sync no /perfil; bloco null é omitido
null    → atravessa o contrato: "—" na tabela, nunca número inventado
race    → useRef(0) seq ou flag cancelled em todo painel com refetch
```

## Landing: prints e QA (`scripts/site/`)

| Script | O que faz |
|---|---|
| `capture_mock.py` | **Caminho recomendado**: Playwright contra o build standalone (:3100) interceptando todas as chamadas `/api/*` com payloads mockados de uma persona exemplar (determinísticos — rerodada gera os mesmos prints); cookie falso (o proxy é otimista); 17 prints em `public/prints/` |
| `capture.py` | Caminho com **sessão real**: login manual em Chromium visível (senha nunca passa pelo script), cookie salvo fora do repo, captura headless com dados reais |
| `verify_site.py` | QA de visitante: raiz renderiza a landing (sem redirect de URL), `/treinos` protege (`/login?next=…`), zero overflow horizontal em 390px e 1440px |

Os payloads do mock seguem os contratos de `src/lib/api.ts` — a lista
canônica de rotas mockadas espelha os endpoints consumidos.

## Build e deploy

- `next build`: na **Vercel** usa o build nativo (`output` sem
  standalone); no **Docker/compose**, multi-stage node:22-alpine com
  `output: "standalone"` → `node server.js`.
- Env: `BACKEND_URL` (resolvida no build — redeploy ao trocar) ·
  `NEXT_PUBLIC_API_URL` (legado de build) · `VERCEL` (desativa
  standalone).
- Scripts: `dev` · `build` · `start` · `lint` (ESLint 9 flat config).

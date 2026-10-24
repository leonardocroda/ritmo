# Frontend — Componentes

Catálogo completo dos componentes por pasta. Legenda: **[C]** client
component (`"use client"`) · **[S]** server component. Nenhum componente
faz fetch direto — todos consomem `src/lib/api.ts`.

## Compartilhados (`src/components/`)

| Componente | Arquivo | Tipo | Papel |
|---|---|---|---|
| `Header` | `Header.tsx` | **[S]** | Top bar: wordmark "ritmo" + pulso de HRV (SVG lime) + `Nav` + `UserMenu` |
| `Nav` | `Nav.tsx` | **[C]** | Top bar desktop (≥md): 5 pills, ativo com `aria-current`, `scrollIntoView` |
| `TabBar` | `Nav.tsx` | **[C]** | Tab bar inferior (<md): fixa, 5 colunas, safe-area, alvo ≥44px |
| `UserMenu` | `UserMenu.tsx` | **[C]** | Chip do usuário: `me()` no mount, display_name + "Sair" (logout + reload) |
| `SyncButton` | `SyncButton.tsx` | **[C]** | "Puxar do Garmin": `POST /api/sync` + polling 2s de `jobs/latest`; estados idle/running/done/error/reauth (instrução da CLI) |
| `Skeleton` | `Skeleton.tsx` | **[S]** | Bloco pulsando no formato da composição que chega (classe `.skeleton`) |
| `PanelSection` | `PanelSection.tsx` | **[S]** | Cabeçalho forte de seção (índice + título + subtítulo sempre visível) — o padrão de clareza AD-009 |

## Home (`src/components/home/`) — todos [C]

| Componente | Papel |
|---|---|
| `HomePanel` | Composição: fetch único `GET /api/home/today`; estados loading/error/empty/ready |
| `VerdictCard` | Herói: frase do veredito, 3 chips de sinal (HRV/sono/forma), strip de carga 7d (BarChart, só hoje acesa) |
| `RoutingChips` | 3 chips que roteiam: último treino → `/treinos/{id}` · volume → `/performance` · countdown → `/performance` |
| `RecommendationCards` | Cards "Recomendação · regra" com tag do porquê e dot semântico |
| `VolumeMini` | Mini de volume 10 semanas (BarChart) + sentença com Δ% e ACWR |
| `PredictionsDigest` | Linha de predições 10K/meia + "ver Performance →" |

## Treinos (`src/components/workouts/`) — todos [C]

| Componente | Papel |
|---|---|
| `WorkoutsList` | Lista paginada (30/pág), filtro Corridas/Todas, "Carregar mais", badge "Avaliado", `requestSeq` anti-race |
| `WorkoutDetail` | Detalhe: estados loading/not-found/error/ready; polling 2s de avaliações pending; composição header → métricas → estrutura → contexto → consistência → IA → voltas |
| `SplitsChart` | Gráfico de voltas em **SVG próprio** (sem Recharts — AD-008): largura ∝ duração da volta, cor por zona VDOT, linha de FC, relevo, tooltip por tap |
| `EvaluateForm` | Intenção: select dos 7 tipos (prefill do inferido) + texto ≤500; bloqueio de duplo clique |
| `EvaluationCard` (+ `EvaluationHistory`) | Card do veredito: selo por veredito, % na zona alvo (número Python), listas, rodapé de auditoria (modelo · tokens · data); histórico anterior |

## Saúde (`src/components/health/`) — todos [C]

| Componente | Papel |
|---|---|
| `HealthPanel` | Seletor de janela **7/30/42/60/90d** (default 60); fetch por janela com seq-guard; 4 seções numeradas; estado vazio geral e por bloco |
| `SleepChart` | Horas de sono vs `ReferenceLine` do piso 7h |
| `SleepStagesChart` | Fases empilhadas (leve/profundo/REM em %) |
| `RemChart` | Linha REM% + banda 21–31% (`ReferenceArea`) |
| `WeekdayPattern` | Deitar/acordar médios + média por dia da semana |
| `HrvChart` | Modelo científico: Scatter das noites + média móvel 7d + banda pessoal (2 Areas) |
| `HrvTable` | Noites HRV com paginação client de 7 linhas |
| `RhrChart` | FC repouso + `ReferenceLine` no baseline |
| `StressChart` | Estresse médio diário; bloco null → card "—" |
| `DoseResponse` | Noites <6h vs ≥6h45: noites, HRV média, score médio |
| `Lifestyle` | Força (streak 2×/sem) e yoga (sessões, média/semana) |

## Performance (`src/components/performance/`)

| Componente | Tipo | Papel |
|---|---|---|
| `PerformancePanel` | **[C]** | Fetch único `GET /api/potential`; 4 blocos narrativos; GapCard inline |
| `VdotTimeline` | **[C]** | ScatterChart por teste/prova + faixa honesta (`ReferenceArea`) + linha do VDOT corrente |
| `PredictionsTable` | **[S]** | 5K/10K/meia/maratona × Garmin/Riegel/VDOT/média/PR — legenda por método sempre visível |
| `DecayTable` | **[S]** | Pace real (PR) vs ideal (VDOT) + Δ%; maior gap destacado |
| `PmcChart` | **[C]** | TSB em barras + linhas CTL/ATL + zero; cards do último dia |
| `Vo2maxTrend` | **[C]** | Linha do VO2max do relógio + selo "estimativa" |

## Perfil (`src/components/profile/`) — todos [C]

| Componente | Papel |
|---|---|
| `ConnectionCard` | Estado da conexão Garmin (Conectado/Reautenticação necessária/Não conectado) + última atualização de tokens |
| `HrValuesCard` | FC máx/repouso/LTHR com badge de fonte e vigência; salvar = `PUT hr-zones` (422 inline no campo); "Voltar a puxar do Garmin" (flip de posse) |
| `HrMethodCard` | Seletor do método (LTHR% · reserva cardíaca · FC máx%) + editor dos percentuais das 5 zonas |
| `HrZonesPreview` | Zonas resultantes em bpm — "salvar → zonas mudam na hora" |
| `HrHistoryList` | Timeline fundida (métricas + configs) por `valid_from` DESC |

## Módulos (`src/lib/`)

| Módulo | Papel |
|---|---|
| `api.ts` | Cliente tipado: `apiFetch` (401 → `/login?next=`), `ApiError`/`AuthError`, 16 endpoints, todos os tipos espelho do backend |
| `format.ts` | PT-BR: pace, duração, km, VDOT, datas wall clock (sem conversão de fuso) |
| `chartTheme.ts` | "Contexto em neutro, um único destaque lime": `chart.*`, props de tick/axis, `tooltipCard`/`legendCaption`; cores de zona vêm do backend (`ZoneMeta.color`) |

## Hierarquia (quem compõe quem)

```text
(app)/layout
├── Header
│   ├── Nav (desktop)
│   └── UserMenu
└── TabBar (mobile)

/            HomePanel → VerdictCard · RoutingChips · RecommendationCards
                                              · VolumeMini · PredictionsDigest
/treinos     WorkoutsList
/treinos/[id] WorkoutDetail → EvaluateForm · EvaluationCard(+History) · SplitsChart
/saude       HealthPanel → SleepChart · SleepStagesChart · RemChart · WeekdayPattern
                          · HrvChart · HrvTable · RhrChart · DoseResponse · Lifestyle
                          · StressChart (cada um sob seu PanelSection)
/performance PerformancePanel → VdotTimeline · PredictionsTable · DecayTable
                                · Vo2maxTrend · PmcChart (cada um sob PanelSection)
/perfil      ConnectionCard · SyncButton · HrValuesCard · HrMethodCard
             · HrZonesPreview · HrHistoryList (sob PanelSections)
```

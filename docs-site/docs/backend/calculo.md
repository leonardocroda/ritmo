# Backend — Motores de Cálculo

Todo número que a UI exibe nasce de **funções puras determinísticas** —
sem I/O, sem LLM, testáveis de frente para trás. Os módulos puros vivem
em `calc.py` de cada domínio e em `app/vdot/`; os services os orquestram
com queries. É a base da AD-003.

## VDOT / Daniels (`app/vdot/`)

- **`daniels.py`** — equações de Jack Daniels: custo de oxigênio por
  distância, `fraction_vo2max`, `calculate_vdot(distância, tempo)`,
  inversão `speed_for_vo2`, `pace_for_fraction` e
  `equivalent_time` (busca binária). Gerou a calibração vigente:
  10K 41:15 → **VDOT 50.2**.
- **`zones.py`** — `ZoneConfig` carrega `data/vdot_zones.json`
  (`VDOT_ZONES_PATH`); **cut points no midpoint** entre zonas;
  `classify(velocidade)` → `easy | marathon | threshold | interval |
  repetition`; `meta()` devolve rótulos PT-BR, faixas e **cores fixas**
  (verde/azul/laranja/vermelho/roxo) — o backend é a fonte única da cor
  de zona (DSN-16).
- **`calibration.py`** — `Calibration` lê os campos raiz do JSON (VDOT
  corrente, fonte, data do teste) — alimenta o painel Performance e o
  payload da avaliação.
- **`calibrate_vdot.py`** — CLI de entrevista: distância + tempo do teste
  → VDOT → zonas + equivalências; grava o JSON (`--check`/`--force`).
  Portar para o app segue na Fase 2.

## PMC / carga de treino (`app/garmin/pmc.py`)

Modelo de Banister com EWMA sobre o `training_load` das atividades
(agregado por dia local, gaps = 0):

| Métrica | Fórmula |
|---|---|
| CTL (fitness) | EWMA com α = 1/42 |
| ATL (fadiga) | EWMA com α = 1/7 |
| TSB (forma) | CTL − ATL |
| ACWR | soma 7d ÷ (soma 28d ÷ 4) — `null` até 28 dias completos |

`recompute(from, today)` reescreve só a janela afetada pelo sync,
semeando da última linha anterior (SYNC-23) — o passado não é recalculado.

## Inferência de tipo (`app/activities/infer.py`)

Calculada **em tempo de leitura** (nunca persistida), sobre splits +
zonas VDOT, com prioridade estrita:

```text
prova (eventType=race)
  > intervalado (≥2 grupos interval/repetition separados por recuperação)
  > limiar (≥3 voltas threshold somando ≥2000 m)
  > tempo (idem marathon)
  > progressivo (2ª metade ≤92% do pace da 1ª)
  > longão (≥16000 m)
  > fácil
```

`derive_structure` soma os passos por `intensityType`
("Aquecimento 2,0 km + …").

## Consistência (`app/activities/metrics.py`)

Gate: corridas **≥8 km com ≥4 voltas**. Metades por distância acumulada:

- `balance_delta_s/pct` — equilíbrio de pace 1ª vs 2ª metade;
- `hr_drift_bpm` — drift cardíaco (exibido ao lado do Δ pace — drift só
  se interpreta a ritmo constante, AD-005);
- `decoupling_pct` — variação % da razão FC/pace entre metades;
- `cadence_fade_spm` — fade de cadência (≥2 voltas com cadência).

## Veredito diário da Home (`app/home/calc.py`)

Cadeia de prioridade fixa **V1→V6** (determinística, sem score, sem LLM —
AD-025); sinal ausente = neutro:

```text
V1 dívida de recuperação → V2 corpo pedindo leve → V3 carga alta
(ACWR > 1.5) → V4 fadiga (TSB < −10) → V5 pronto pra qualidade
→ V6 dia comum
```

Complementam: **recomendações R1–R5** (cap 3, taper de prova ≤14 dias
dispara independente do veredito, cada uma com a tag do porquê),
`sleep_delta` (vs média das 7 noites anteriores), `weekly_volume`
(semanas ISO, média 4 semanas, série de 10) e o digest de predições.

## Modelo de HRV e sono (`app/health/calc.py`)

- **HRV (AD-010, modelo Altini/HRV4Training)**: linha = média móvel 7d
  (lacunas não quebram); banda por dia = janela 60d média ± 0,75 × DP
  (só com ≥14 valores); status local BALANCED/UNBALANCED — null =
  "coletando linha de base". O status cru da Garmin segue persistido mas
  fora da UI.
- **Sono**: piso 7h; REM na banda 21–31%; padrão deitar/acordar por dia
  da semana; regularidade por **média circular** (±12h).
- **Dose-resposta**: noites curtas (<6h) vs adequadas (≥6h45) — preço de
  dormir mal em HRV e score; faixa 6h–6h45 é neutra.
- **Estilo de vida**: força com streak de 2×/semana (checklist ISO).

## Potencial (`app/potential/calc.py`)

- **Riegel**: T2 = T1 × (D2/5000)^1.06 — âncora fixa no PR de 5K (sem
  âncora → "—").
- **Timeline VDOT**: PRs canônicos + provas máximas (dedup: PR com
  certificado na mesma data não vira 2 pontos; PR sem data não plota);
  demonstrado = melhor VDOT; **faixa honesta** (AD-004) — corrente →
  demonstrado sombreado.
- **Predições 4×** por distância: Garmin (sync) · Riegel · equivalência
  VDOT · média honesta (só das presentes) + PR histórico.
- **Decay**: pace real do PR vs ideal do VDOT corrente, Δ% sinalizado
  (negativo = gap de execução/especificidade, não de motor).

## Zonas de FC (`app/profile/calc.py`)

- Defaults por método (AD-021): **LTHR%** 65/80/89/95/100 (Z5 aberta) ·
  **reserva cardíaca/Karvonen** 50/60/70/80/90 · **FC máx%**
  50/60/70/80/90 (Z5 fecha em 100%).
- `validate_bounds` — guardrails: cadeia ascendente, zonas com ≥1 ponto,
  Z5 conforme o método (422 aponta a zona exata).
- `zones_bpm` — derivação por método: lthr %×LTHR; fcr Karvonen
  (FCrest + %(FCmax−FCrest)); fcmax %×FCmax. **Derivada na leitura, com
  as métricas/config vigentes na data consultada** (effective-dated,
  padrão Strava — o passado nunca é reclassificado).

# Intenções de avaliação: repetição + outro — Tasks

**Design**: não há (mudança pontual, sem novas decisões arquiteturais — estende contratos existentes)
**Status**: Planned

## Test Coverage Matrix

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Backend schemas (IntentType) | unit | 9 tipos aceitos; 10º tipo rejeitado | `backend/tests/test_evaluation_schemas.py` | `cd backend; uv run pytest` |
| Backend payload (TARGET_ZONES) | integration (DB semeados) | repeticao→["repetition"] com pct exato; outro→zona_alvo ausente | `backend/tests/test_evaluation_payload.py` | `cd backend; uv run pytest` |
| Backend prompt (regra "outro") | unit | marcador da regra presente no SYSTEM_PROMPT_V1 | `backend/tests/test_evaluation_prompt.py` | `cd backend; uv run pytest` |
| Frontend api.ts | none | tipos espelham backend | `frontend/src/lib/api.ts` | `cd frontend; npm run build; npm run lint` |
| Frontend format.ts + EvaluateForm | none | rótulos PT-BR + 9 opções no select | `frontend/src/lib/format.ts`, `EvaluateForm.tsx` | `cd frontend; npm run build; npm run lint` |

## Gate Check Commands

| Gate Level | Command |
| ---------- | ------- |
| Quick | `cd backend; uv run pytest tests/test_evaluation_schemas.py tests/test_evaluation_payload.py tests/test_evaluation_prompt.py` |
| Build | `cd frontend; npm run build; npm run lint` |
| Commit | `python .opencode/skills/tlc-spec-driven/scripts/check_commit.py --message "<msg>"` |

---

## Task Breakdown

### T1: Backend schemas — IntentType expande para 9 tipos

**What**: `backend/app/evaluation/schemas.py`: `IntentType` Literal passa de 7 para 9 tipos, adicionando `"repeticao"` e `"outro"` (ASCII, sem acento — mesmo padrão de `facil`/`longao`).
**Where**: `backend/app/evaluation/schemas.py` (modify)
**Depends on**: None
**Requirement**: EVAL-28

**Done when**:
- [ ] `IntentType` é `Literal["prova","intervalado","limiar","tempo","progressivo","longao","facil","repeticao","outro"]`
- [ ] Teste unitário: os 9 tipos são aceitos; um 10º tipo (ex.: "recuperacao") é rejeitado
- [ ] Gate quick passa; contagem de testes não cai

**Tests**: unit
**Gate**: quick
**Commit**: `feat(evaluation): intent types repeticao e outro`

---

### T2: Backend payload — TARGET_ZONes mapeia repeticao e outro

**What**: `backend/app/evaluation/payload.py`: `TARGET_ZONES` ganha `"repeticao": ["repetition"]` e `"outro": None` (sem zona alvo única, como progressivo/prova).
**Where**: `backend/app/evaluation/payload.py` (modify)
**Depends on**: T1
**Requirement**: EVAL-26, EVAL-27

**Done when**:
- [ ] `repeticao` mapeia para `["repetition"]`; `outro` mapeia para `None`
- [ ] Teste: intenção `repeticao` → `zona_alvo == {"zonas": ["repetition"], "pct_zona_alvo": <exato>}`
- [ ] Teste: intenção `outro` → `"zona_alvo" not in payload`; `tempo_por_zona_pct` continua presente
- [ ] Gate quick passa

**Tests**: integration
**Gate**: quick
**Commit**: `feat(evaluation): payload zona alvo repeticao e outro`

---

### T3: Backend prompt — regra "outro" dá peso ao texto; repetição compara contra zona repetition

**What**: `backend/app/evaluation/prompt.py`: adicionar instrução de que, quando a intenção é "outro", o texto livre é a fonte principal para julgar execução vs intenção (números do payload continuam como fonte da verdade, nunca recalculados). Reforçar que "repetição" compara contra a zona de repetição do VDOT.
**Where**: `backend/app/evaluation/prompt.py` (modify)
**Depends on**: None
**Requirement**: EVAL-29

**Done when**:
- [ ] Prompt contém regra explícita para intenção "outro": texto livre orienta o julgamento, payload confirma os números
- [ ] Prompt menciona que "repetição" é julgado contra a zona de repetição do VDOT
- [ ] Teste unitário: marcadores da regra estão presentes em `SYSTEM_PROMPT_V1`
- [ ] Gate quick passa

**Tests**: unit
**Gate**: quick
**Commit**: `fix(evaluation): prompt regra outro + repeticao`

---

### T4: Frontend api.ts — InferredType expande para 9 tipos

**What**: `frontend/src/lib/api.ts`: `InferredType` union ganha `"repeticao" | "outro"`.
**Where**: `frontend/src/lib/api.ts` (modify)
**Depends on**: T1
**Requirement**: EVAL-28

**Done when**:
- [ ] `InferredType` inclui os 9 tipos
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build
**Commit**: `feat(frontend): InferredType repeticao e outro`

---

### T5: Frontend format.ts — rótulos PT-BR para repeticao e outro

**What**: `frontend/src/lib/format.ts`: `TYPE_LABELS` ganha `repeticao: "Repetição"` e `outro: "Outro"`.
**Where**: `frontend/src/lib/format.ts` (modify)
**Depends on**: T4
**Requirement**: EVAL-26, EVAL-27

**Done when**:
- [ ] `formatInferredType("repeticao") == "Repetição"`; `formatInferredType("outro") == "Outro"`
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build
**Commit**: `feat(frontend): rótulos PT-BR repeticao e outro`

---

### T6: Frontend EvaluateForm — 9 opções no select

**What**: `frontend/src/components/workouts/EvaluateForm.tsx`: `INTENT_OPTIONS` passa de 7 para 9 tipos, incluindo `"repeticao"` (depois de `intervalado`) e `"outro"` (por último).
**Where**: `frontend/src/components/workouts/EvaluateForm.tsx` (modify)
**Depends on**: T4, T5
**Requirement**: EVAL-26, EVAL-27

**Done when**:
- [ ] Select renderiza 9 opções na ordem: Fácil, Tempo, Limiar, Intervalado, Repetição, Longão, Progressivo, Prova, Outro
- [ ] Pré-preenchimento com `inferred_type` continua funcionando para os 9 tipos
- [ ] `npm run build` + `npm run lint` verdes

**Tests**: none
**Gate**: build
**Commit**: `feat(frontend): select de intenção com repetição e outro`

---

### T7: Regressão + build + commit

**What**: Rodar toda a suite de evaluation (pytest) + build/lint do frontend para garantir regressão zero, depois commit atômico.
**Where**: backend + frontend
**Depends on**: T1..T6
**Requirement**: todos

**Done when**:
- [ ] `cd backend; uv run pytest` verde (todos os testes de evaluation + activities)
- [ ] `cd frontend; npm run build; npm run lint` verde
- [ ] Commit com mensagem Conventional Commits aprovada pelo `check_commit.py`

**Tests**: unit + integration + build
**Gate**: quick + build
**Commit**: `feat(evaluation): intenção repetição e outro na avaliação`

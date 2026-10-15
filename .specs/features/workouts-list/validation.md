# Lista de Treinos + Splits — Validation

**Date**: 2026-10-15
**Spec**: `.specs/features/workouts-list/spec.md`
**Diff range**: `5584d44^..HEAD` (16 commits: T1–T7 backend, T8–T13 frontend+docs, T14 ajustes de UAT; 38 arquivos, +4189/−67)
**Verifier**: sub-agente independente (author ≠ verifier) — árvore real intacta; mutações só em worktree descartável

---

## Task Completion

| Task | Status | Notas |
| ---- | ------ | ----- |
| T1 Cadência/temperatura por volta | ✅ Done | `models.py:86-87` (colunas nullable), `mappers.py:94-95` (`averageRunCadence`/`averageTemperature` — nomes da sonda real), `upserts.py:36-40` (`_SPLIT_FIELDS`); +5 testes (mappers 2, upserts 3) |
| T2 Caminho do arquivo de zonas | ✅ Done | `config.py:29` (default `data/vdot_zones.json`), `Dockerfile` `COPY data ./data` + `.dockerignore` sem `data`; 2 testes em `test_workouts_config.py:11,17`; smoke real no container (`ls data/vdot_zones.json` + `load_zone_config` → 5 zonas) |
| T3 Zonas VDOT (load/classify/meta) | ✅ Done | `vdot/zones.py` (121 linhas); 13 testes em `test_vdot_zones.py` com cortes 4:41/4:29/4:07/3:45 literais do spec |
| T4 Métricas de consistência | ✅ Done | `activities/metrics.py` (139 linhas); 12 testes em `test_activity_metrics.py` vs aritmética manual |
| T5 Tipo inferido + estrutura | ✅ Done | `activities/infer.py` (165 linhas); 21 testes em `test_activity_infer.py` (um por regra + prioridade + strides reais da sonda) |
| T6 Endpoint lista | ✅ Done | `activities/service.py:78-124`, `router.py:103-116` montado em `main.py:47`; 10 testes de lista em `test_activities_api.py` |
| T7 Endpoint detalhe | ✅ Done | `service.py:127-243`, `router.py:119-129`; 10 testes de detalhe em `test_activities_api.py` |
| T8 api.ts + format.ts | ✅ Done | `frontend/src/lib/api.ts:87-229`, `format.ts` (62 linhas); build/lint exit 0 |
| T9 Nav + placeholders + redirect | ✅ Done | `Nav.tsx`, `Header.tsx:16`, `page.tsx:6` (redirect `/`→`/treinos`), placeholders `/hoje` `/potencial` `/saude`; build/lint exit 0 |
| T10 Lista `/treinos` | ✅ Done | `WorkoutsList.tsx` (208 linhas); build/lint exit 0 |
| T11 Detalhe `/treinos/[id]` | ✅ Done | `WorkoutDetail.tsx` (287 linhas) + server page com `await params` e validação numérica (`treinos/[id]/page.tsx:29-31`); build/lint exit 0 |
| T12 Gráfico de splits | ✅ Done | `SplitsChart.tsx` (430 linhas, SVG próprio); build/lint exit 0 |
| T13 Validação real + docs | ✅ Done | `README.md` §"Painel Treinos" + validação real 15/10/2026 (tipos em 4 treinos conhecidos; consistência do longão vs cálculo manual; 170 testes) |
| T14 Ajustes de UAT no gráfico | ✅ Done | commit `a803911`: eixo Y pace ticks 60s (`SplitsChart.tsx:206-254`), eixo Y FC min/meio/máx com caso degenerado (`:212-220`), distância da volta no tooltip (`:96-101,390`) — **checkboxes "Done when" de T14 em tasks.md permanecem desmarcados** (bookkeeping, ver Gaps Ranqueados #2) |

---

## Spec-Anchored Acceptance Criteria

Valores afirmados nos testes conferem com os literais do spec (lição L-001: cortes 4:41/4:29/4:07/3:45, fórmula do pace, gate 8000/4 voltas, 92%, 16km, 2000m — verificados por leitura integral; os midpoints exatos são recalculados no teste a partir do JSON, não de constantes do módulo).

**Convenção da matriz**: frontend sem infra de testes (decisão da Test Coverage Matrix: build + lint + UAT). Para ACs de UI, a evidência é implementação (`file:line`) + gates + UAT real de 15/10/2026 (containers reconstruídos, usuário confirmou as telas; ajustes de leitura viraram T14).

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| ------------------------- | -------------------- | ----------------------- | ------ |
| TRN-01: nav dos 4 painéis alongside do "Puxar do Garmin", legível 390px | 4 painéis no header global | `frontend/src/components/Nav.tsx:18-23` (PANELS = Hoje/Treinos/Potencial/Saúde) + `Header.tsx:16-17` (Nav + SyncButton); 390px: `Nav.tsx:74` overflow-x-auto + scrollIntoView do ativo `:38-40`; UAT real 15/10 | ✅ PASS (per matriz) |
| TRN-02: painel ativo marcado no header | ativo = pathname === href ou startsWith(href+"/") | `Nav.tsx:25-31` (`activePanel` com as duas regras do design), `:51` `aria-current="page"`, `:52-56` estilo bg-accent; UAT real | ✅ PASS (per matriz) |
| TRN-03: placeholders com nome + "em construção"; `/treinos` exibe lista; `/` → `/treinos` | 3 placeholders + lista + redirect | `PanelPlaceholder.tsx:12` ("em construção") montado em `app/hoje|potencial|saude/page.tsx`; `app/treinos/page.tsx:9` renderiza `<WorkoutsList />`; `app/page.tsx:6` `redirect("/treinos")`; UAT real | ✅ PASS (per matriz) |
| TRN-04: lista = corridas, `start_time DESC` desempate `id DESC`, `{items,total,limit,offset}` | ordem estável + envelope exato | `service.py:98` `.order_by(start_time.desc(), id.desc())`; `test_activities_api.py:141-144` — `total==2`, `names == ["Londrina - Strides", "Easy Run"]` (DESC); `:206-215` — empate → `[second.id, first.id]`; `:121-125` — envelope exato `{"items": [], "total": 0, "limit": 30, "offset": 0}` | ✅ PASS |
| TRN-05: `activity_type=all` inclui todas; omitido → só corridas | filtro default running/trail_running | `service.py:88-89` (`RUNNING_TYPES` in-filter quando ≠ all); `router.py:105` Literal default `"running"`; `test_activities_api.py:168-174` — `total==3` com cycling+yoga, `yoga.inferred_type is None` | ✅ PASS |
| TRN-06: pace = `duration×1000/distance` quando >0, senão null; UI exibe só quando não-nulo | fórmula exata + null | `service.py:27-29`; `test_activities_api.py:149` — `pace_s == 250.0` (375×1000/1500); `:172` — yoga (0m) `pace_s is None`; `:174` — cycling `== 180.0`; UI `WorkoutsList.tsx:62-64` (pace ≠ null ? pace : duração) | ✅ PASS |
| TRN-07: tipo inferido por regras determinísticas na prioridade do spec, só banco | 7 regras, ordem estrita | `infer.py:120-138` (prova>intervalado>limiar>tempo>progressivo>longao>facil); 21 testes: `test_activity_infer.py:37` (proza vence tudo), `:176-187` (intervalado vence limiar), `:166-173` (tempo vence longão), `:146-151` (fronteira 92% inclusiva), `:159-163` (16km inclusivo); via API `test_activities_api.py:232-235` (facil/intervalado) | ✅ PASS |
| TRN-08: `evaluated=true` → badge "Avaliado" no item | badge no item da lista | payload: `test_activities_api.py:238-245` — `items[0]["evaluated"] is True`; UI `WorkoutsList.tsx:47-51` (badge "Avaliado" quando `item.evaluated`); UAT real | ✅ PASS (per matriz) |
| TRN-09: limit fora [1,100] ou offset<0 → 422 sem executar query | HTTP 422 | `router.py:106-107` (`Query(default=30, ge=1, le=100)`, `Query(default=0, ge=0)` — validação FastAPI no signature, antes do handler); `test_activities_api.py:218-222` — `limit=0`, `limit=101`, `offset=-1` → todos `status_code == 422`. Nota: "sem executar a query" é garantia estrutural do FastAPI (validação de signature precede o corpo do endpoint) — comportamento observável 422 testado | ✅ PASS |
| TRN-10: banco vazio → estado vazio apontando "Puxar do Garmin", sem erro | 200 vazio + CTA na UI | API: `test_activities_api.py:121-125` — 200 com página vazia; UI `WorkoutsList.tsx:175-180` ("Use o botão "Puxar do Garmin" no topo…"); UAT real | ✅ PASS (per matriz) |
| TRN-11: item exibe data, nome, tipo, distância, pace/duração, FC | campos do item | payload: `test_activities_api.py:145-151` (start_time/activity_type/pace_s/avg_hr/evaluated); UI `WorkoutsList.tsx:53-69` (data+tipo+km, pace ou duração, FC quando existe); UAT real | ✅ PASS (per matriz) |
| TRN-12: API falha → mensagem de erro sem quebrar navegação | erro inline | `WorkoutsList.tsx:169-173` (mensagem inline; nav vive fora do `<main>`); UAT real | ✅ PASS (per matriz) |
| TRN-13: id inexistente → 404 | HTTP 404 | `router.py:126-128`; `test_activities_api.py:271-275` — `status_code == 404`, `detail == "atividade não encontrada"` | ✅ PASS |
| TRN-14: cada volta com pace válido em exatamente 1 zona (cut points de midpoint); pace inválido → zone=null | classificação total/exclusiva | `zones.py:84-96` (4 cuts, abaixo→easy, acima→repetition); `test_vdot_zones.py:73-94` — fronteiras 281/280, 269/268, 247/246, 225/224 (4:41/4:29/4:07/3:45 do spec); `:103-119` — borda exata → zona mais rápida (midpoints recalculados do JSON); `:122-126` — `classify(None/0/-3.5) is None`; API `test_activities_api.py:390-398` (6/6 voltas do strides com zona) e `:402-416` (dist 0 → `zone is None`) | ✅ PASS |
| TRN-15: payload inclui metadados das zonas (chave, rótulo, faixa) p/ legenda | 5 zonas com key/label/pace_range/color | `zones.py:98-108`; `test_activities_api.py:324-327` — `len(zones)==5` e `zones[0] == {"key": "easy", "label": "Easy", "pace_range": "5:51–4:53/km", "color": "#22c55e"}`; unit `test_vdot_zones.py:134-155` (5 zonas, faixas e cores literais) | ✅ PASS |
| TRN-16: gráfico composto — barras por volta com largura proporcional à duração, cor pela zona, linha de FC, relevo, legenda | largura ∝ duração (decisão do usuário) | `SplitsChart.tsx:151-166` (`width = PLOT_W × duration_s/totalDuration`), `:297` (`fill = zone.color` do payload), FC `:318-335` (polyline + ponto no meio da barra), relevo `:269-286` (eixo próprio), legenda `:59-88`; UAT real 15/10 confirmou (feedback de leitura virou T14) | ✅ PASS (per matriz) |
| TRN-17: linha de FC em cor distinta da cor da zona interval | cor reservada ≠ interval (vermelho) | **teste Python no payload** (como a matriz exige): `test_activities_api.py:329-332` — `hr_color == "#f8fafc"` e `hr_color != interval_color`; unit `test_vdot_zones.py:158-162` — `interval_color != "#f8fafc"`; fonte `zones.py:28` | ✅ PASS |
| TRN-18: pace fora [180,420] → barra clampada; valor real no tooltip | clamp no desenho, real no tooltip | `SplitsChart.tsx:157-163` (`Math.min(420, Math.max(180, pace_s))` + piso 2.5px), tooltip `:389` (`formatPace(active.split.pace_s)` — não clampado); UAT real (voltas de recuperação no fundo, sem barra negativa) | ✅ PASS (per matriz) |
| TRN-19: sem splits → resumo sem gráfico/consistência + nota "sem voltas registradas" | resumo puro | API `test_activities_api.py:419-434` — `splits == []`, `consistency is None`, `structure is None`; UI `WorkoutDetail.tsx:270-272` ("sem voltas registradas") e `:273` (gráfico só com splits); UAT real | ✅ PASS |
| TRN-20: cabeçalho com data, nome, tipo, distância, duração, pace, FC média/máx, cadência, elevação — omitido quando null | métricas condicionais | payload: `test_activities_api.py:302-309`; UI `WorkoutDetail.tsx:157-181` — cada `<Metric>` condicional (`pace_s !== null`, `max_hr !== null`, `avg_cadence !== null`, `elevation_gain_m !== null`); UAT real | ✅ PASS (per matriz) |
| TRN-21: ≥8000m e ≥4 voltas → bloco consistency com equilíbrio (s/km + %), drift (bpm), decoupling (%), fade (spm) | gate inclusivo + 4 métricas | `metrics.py:100` (`< 8000 or < 4 → None`); `test_activity_metrics.py:85-90` — exatamente 8000m/4 voltas → `result is not None`, `first_half_pace_s == 300.0`; valores vs manual `:97-111` (`balance_delta_s == -10.0`, `pct == -3.3`, `decoupling == 3.4`, `fade == -2.0`); via API `test_activities_api.py:311-322` (dict completo, incl. `decoupling_pct == 7.1` com FC 140→145) | ✅ PASS |
| TRN-22: <8000m ou <4 voltas → consistency=null, UI oculta | null + tabela oculta | `test_activity_metrics.py:74-83` (7999.9 → None; 3×3000m/9000m → None); API `test_activities_api.py:399` (strides 3600m → None), `:457-470` (9000m mas 3 voltas → None); UI `WorkoutDetail.tsx:220` (seção só com `consistency !== null`) | ✅ PASS |
| TRN-23: metades por distância acumulada; funções puras determinísticas | mesma entrada → mesmos valores | `metrics.py:27-48` (≥50% fecha a 1ª; atravessadora fica na 1ª); `test_activity_metrics.py:43-66` (3 fixtures de divisão, incl. `first == [3000, 1000]`), `:187-190` (`consistency_metrics(laps, 8000) == consistency_metrics(laps, 8000)`) | ✅ PASS |
| TRN-24: drift cardíaco exibido junto do Δ pace das metades | Δ pace ao lado do drift (AD-005) | `WorkoutDetail.tsx:238-249` — linhas "Δ pace (1ª → 2ª)" e "Drift cardíaco" na mesma tabela; UAT real (longão com ambos visíveis) | ✅ PASS (per matriz) |
| TRN-25: sem cadência suficiente → campo de fade omitido | chave ausente, não null | `metrics.py:130-138`; `test_activity_metrics.py:158-167` — 2ª metade com 1 volta com cadência → `"cadence_fade_spm" not in result` | ✅ PASS |
| TRN-26: sono/HRV/RHR da data local de início; null quando ausente; UI só os presentes | contexto do dia | `service.py:153-170` (`day = start_time.date()`); `test_activities_api.py:473-501` — `sleep == {"duration_s": 28800.0, "score": 85}`, `hrv == {"value": 48.0, ...}`, `rhr == {"value": 42}`; `:504-513` — dia sem dados → `context == {"sleep": None, "hrv": None, "rhr": None}`; UI `WorkoutDetail.tsx:196-213` (chips condicionais) | ✅ PASS |
| TRN-27: ≥1 volta com temperatura → média ponderada por duração; nenhuma → campo omitido | ponderação + omissão | `service.py:132-145,171-173`; `test_activities_api.py:491-500` — (22×300 + 24×300)/600 → `temperature_c == 23.0`; `:353-356` — sem temperatura → `"temperature_c" not in context` | ✅ PASS |
| TRN-28: zero chamadas à API do Garmin nos endpoints (AD-002) | nenhum import do gateway no domínio | `test_activities_api.py:248-257` — varre todos os módulos de `activities/` afirmando `"from app.garmin"` e `"import app.garmin"` ausentes; service só lê models (`service.py:19`) | ✅ PASS |
| TRN-29: `averageRunCadence` → `Split.avg_cadence`; ausente → NULL | gravação + NULL | `mappers.py:94`; `test_garmin_mappers.py:137-146` — `rows[0]["avg_cadence"] == 155.2` (sonda real); `test_garmin_upserts.py:216-236` — coluna gravada `first.avg_cadence == 155.2` no Postgres; `:239-252` — sem campo → `first.avg_cadence is None` | ✅ PASS |
| TRN-30: `averageTemperature` → `Split.avg_temperature`; ausente → NULL | gravação + NULL | `mappers.py:95`; `test_garmin_mappers.py:139-143` — `rows[0]["avg_temperature"] == 22.0`, `rows[1] == 22.1`; `test_garmin_upserts.py:230-236` — `first.avg_temperature == 22.0`; `:248-252` — `is None` | ✅ PASS |
| TRN-31: re-upsert idempotente por `(activity_id, idx)` com os campos novos | contagem estável 2× | `test_garmin_upserts.py:255-274` — 2× upsert → `_count(db, Split) == 2` e valores preservados (`avg_cadence == 155.2`, `avg_temperature == 22.0`) | ✅ PASS |
| TRN-32: estrutura derivada — soma passos consecutivos por tipo; tipo único → rótulo | port de derive_structure | `infer.py:141-165`; `test_activity_infer.py:234-241` — `"Aquecimento 2,0km + Corrida 7,1km + Desaquecimento 2,0km"` (exato do design); `:244-246` — tipo único → `"Corrida"`; `:249-256` (descanso interrompe); via API `test_activities_api.py:384-388` (strides → string completa) | ✅ PASS |

**Status**: ✅ 32/32 ACs com evidência `file:line` + asserção/estrutura ancorada no literal do spec. 0 spec-precision gaps bloqueantes (notas: TRN-09 "sem executar a query" é garantia estrutural do FastAPI; TRN-24 em dados degenerados — voltas com FC mas sem pace válido — exibiria drift sem Δ pace, consistente com o princípio "nenhum número inventado").

---

## Edge Cases (spec.md)

- [x] Não-corrida no detalhe (modo all) → resumo sem gráfico/zonas/consistência: `test_activities_api.py:437-454` (yoga: `inferred_type is None`, `pace_s is None`, `consistency is None`)
- [x] Volta com `avg_hr=null` → ponto ausente da linha (conecta existentes): `SplitsChart.tsx:178` (`hrBars = bars.filter(avg_hr !== null)`) — per matriz (UI)
- [x] `vdot_zones.json` ausente/inválido → 500 "zonas VDOT não configuradas": `router.py:93-100`; `test_activities_api.py:278-286` — `detail == "zonas VDOT não configuradas"` (mensagem exata)
- [x] Todas as voltas sem pace → eixo vazio + nota "sem voltas com pace": `SplitsChart.tsx:116-146` — per matriz (UI)
- [x] Mesmo `start_time` → desempate `id DESC`: `test_activities_api.py:206-215`
- [x] `total < offset` → `items=[]` sem erro: `test_activities_api.py:177-185` (`offset=999` → `{"items": [], "total": 3, ...}`)
- [x] Exatamente 8000m → tabela aparece (inclusivo): `test_activity_metrics.py:85-90` + API `test_activities_api.py:311`
- [x] Volta com distance=0/duration=0 → pace null, zone null, conta para estrutura/relevo: `test_activities_api.py:402-416` (`km_label` acumula corretamente — volta nula não avança)

---

## Discrimination Sensor

**Tier**: lightweight expandido (painel central do MVP) — 5 mutações comportamentais nos pontos de maior risco do domínio novo.
**Scratch**: `git worktree add C:\Users\leona\AppData\Local\Temp\opencode\verifier-wt HEAD` (detached em `a803911`), testes rodados com o venv do repositório principal (`backend\.venv`) a partir do backend do worktree; probe confirmou `app.__file__` resolvendo para a cópia do worktree (o `.pth` editável aponta para o repo principal — cwd vence). Controle não-mutado: 46 unit tests verdes antes da 1ª mutação. Nenhuma mutação tocou a árvore real — `git status --porcelain` = `?? .specs/features/workouts-list/design.md` antes e depois; worktree removido com `--force`.

| # | Mutante | file:line (scratch) | Descrição | Morto? |
| - | ------- | ------------------- | --------- | ------ |
| M1 | semântica de borda de zona | `vdot/zones.py:90` | `speed < cuts[1]` → `<=` (borda exata marathon/threshold muda de zona) | ✅ Killed — `test_classify_exact_cut_belongs_to_faster_zone` (1 failed) |
| M2 | gate de consistência | `activities/metrics.py:100` | `distance_m < 8000` → `<= 8000` (limite deixa de ser inclusivo) | ✅ Killed — 6 failed, incl. `test_consistency_gate_is_inclusive` e `test_consistency_negative_split_values` |
| M3 | regra do intervalado | `activities/infer.py:128` | `_count_work_groups >= 2` → `>= 3` (exige 3 grupos) | ✅ Killed — 3 failed (`test_intervalado_two_groups_separated_by_easy_zone`, `..._recovery_by_intensity_type_rest`, `test_intervalado_beats_limiar`) |
| M4 | ordenação da lista | `activities/service.py:98` | `start_time.desc()` → `.asc()` | ✅ Killed — 2 failed (`test_list_defaults_to_running_newest_first`, `test_list_pagination_pages_concatenate_without_duplicates`) |
| M5 | premissa das metades | `activities/metrics.py:46` | `accumulated >= target` → `>` (volta que fecha os 50% iria para a 2ª metade) | ✅ Killed — 6 failed, incl. `test_split_halves_even_laps_close_at_half` e `test_split_halves_crossing_lap_stays_in_first` |

**Result**: **5/5 killed, 0 sobreviventes** — PASS ✅. Os testes discriminam bordas de zona (midpoint exato), gate inclusivo de 8000m, regra de grupos do intervalado, ordenação estável da lista e a premissa de divisão por distância acumulada.

---

## Interactive UAT Results

UAT real realizada pelo usuário em 15/10/2026 (containers reconstruídos; evidência documentada em tasks.md T13 e README "Validação real"):

| # | Test | Result | Details |
| - | ---- | ------ | ------- |
| 1 | Lista/detalhe/gráfico com dados reais (fácil, strides, longão) | ✅ Pass | usuário confirmou as telas; tipos inferidos conferidos (strides → intervalado, 8x800m → intervalado, 2x3km limiar → limiar, 16km → longão — README) |
| 2 | Leitura do gráfico (eixos/tooltip) | ✅ Pass (após T14) | feedback: "eixos rotulados + distância da volta no tooltip" → virou T14, implementado em `a803911` e re-confirmado |
| 3 | Navegação 390px | ✅ Pass (com fix) | scroll do painel ativo → commit `9da9573` (fix ui nav mobile) |

---

## Code Quality

| Principle | Status |
| --------- | ------ |
| Minimum code (nada além do pedido) | ✅ diff na superfície planejada (T1–T14); out-of-scope respeitado (sem busca, sem edição/exclusão, sem calibração, sem story) |
| Surgical changes / só arquivos da task | ✅ 38 arquivos, todos mapeados a T1–T14 (+spec/tasks/docs da própria feature) |
| No scope creep | ✅ |
| Matches patterns | ✅ docstrings PT-BR, padrão router/service do garmin-sync, SQLAlchemy 2.x, client components no padrão SyncButton |
| Spec-anchored outcome check | ✅ literais do spec nos testes (cortes, gate, fórmulas, mensagens 404/500, envelope de paginação); midpoints recalculados no teste a partir do JSON |
| Per-layer Coverage Expectation | ✅ domínio 1:1 com ACs (zones/metrics/infer); rotas happy+edge+error (200/404/422/500, vazio, além-do-fim, empate); integração no Postgres real do compose |
| Every test maps to a spec requirement | ✅ cada teste cita TRN-NN/T#/edge no docstring; `test_workouts_config.py` cobre T2 |
| Documented guidelines followed | ✅ README §Testes (uv + Postgres do compose), `frontend/AGENTS.md` (Next 16 — `PageProps<"/treinos/[id]">`, `await params`), L-001/L-002 aplicadas |

---

## Gate Check

- **Gate commands**: `cd backend; uv run pytest` · `cd frontend; npm run build; npm run lint` · smoke no container
- **Backend**: **170 passed, 0 failed, 0 skipped** (121.41s, exit 0; 1 warning pré-existente `StarletteDeprecationWarning` do TestClient, não relacionado)
- **Frontend**: `npm run build` exit 0 (rotas /_not-found, /hoje, /potencial, /saude, /treinos, /treinos/[id]) · `npm run lint` exit 0
- **Container smoke**: `ritmo-backend` contém `data/vdot_zones.json`, `load_zone_config` → 5 zonas; API real: `GET /api/activities?limit=3` → 148 atividades (strides → `intervalado`), `GET /api/activities/240` → 5 zonas, 11 splits, consistency presente, `hr_color=#f8fafc`
- **Test count before feature**: 97 (fim do garmin-sync)
- **Test count after feature**: 170 (+73 = zones 13 + metrics 12 + infer 21 + api 20 + config 2 + mappers 2 + upserts 3)
- **Delta**: +73 novos; nenhum teste deletado (mappers/upserts só cresceram); nenhuma asserção enfraquecida
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Success Criteria

- [x] `/treinos` lista corridas reais com tipo inferido; detalhe classifica todas as voltas com pace válido em zona — API real (148 atividades; strides `intervalado`; nenhuma volta com pace válido sem zona: classify cobre todo o intervalo) + UAT
- [x] Zero chamadas à API do Garmin nos endpoints — `test_activities_domain_never_imports_garmin_gateway` (`test_activities_api.py:248-257`)
- [x] Consistência determinística — `test_activity_metrics.py:187-190` + UAT (longão conferido vs cálculo manual: Δ pace −4,65s/km · drift +9,98 bpm · decoupling +7,9% — README)
- [x] Navegação completa e placeholders em 390px — UAT real (DevTools) + fix `9da9573`; LAN ficou explicitamente fora de escopo no spec
- [x] Suite verde no Postgres do compose, incluindo strides/pace nulo/sem splits — 170 passed

---

## Requirement Traceability Update

32/32 TRN-NN verificados com evidência. O Verifier não altera `spec.md` (restrição de escrita desta validação) — statuses `Implemented → Verified` devem ser atualizados pelo orchestrator ao aceitar este veredito.

---

## Gaps Ranqueados

1. **Nenhum gap de código ou de cobertura.** 32/32 ACs, 8/8 edge cases, 5/5 mutantes mortos, gates verdes.
2. **Bookkeeping (não-bloqueante)**: tasks.md deixa os 4 checkboxes "Done when" de **T14 desmarcados** e o header `Status: In Progress (Lote 1: T1–T7 em execução)` stale — a T14 está implementada e commitada (`a803911`, verificado no código: `SplitsChart.tsx:206-220,96-101`). → orchestrator deve marcar os boxes e o status ao atualizar o spec.
3. **Nota, sem ação**: TRN-09 "sem executar a query" é verificado estruturalmente (validação `Query` no signature do endpoint, `router.py:106-107`) — o teste cobre o outcome observável (422); nenhum teste precisaria espiar a sessão.
4. **Nota, sem ação**: UI (TRN-01/02/03/08/10/11/12/16/18/20/24) coberta por decisão da matriz (build+lint+UAT) sem asserção automatizada — quando a Fase 1 ganhar infra de teste frontend (ex.: Playwright), cobrir os estados da lista e do gráfico.

---

## Summary

**Overall**: ✅ PASS — Ready

**Spec-anchored check**: 32/32 ACs com `file:line` + asserção conferida ao literal do spec; 8/8 edge cases; 0 spec-precision gaps bloqueantes
**Sensor**: 5/5 mutações mortas, 0 sobreviventes (worktree descartável; porcelain idêntico ao baseline antes/depois)
**Gate**: 170 passed / 0 failed / 0 skipped · frontend build+lint exit 0 · smoke real no container OK
**Test integrity**: 97 → 170 (+73), nenhum teste deletado, nenhuma asserção enfraquecida

**What works**: pipeline de leitura completo end-to-end (sync grava cadência/temperatura → zonas VDOT carregadas do JSON calibrado → lista paginada com tipo inferido sem N+1 → detalhe com voltas classificadas, consistência determinística, contexto do dia e estrutura → UI com nav, lista, detalhe e gráfico SVG proporcional), validado por 170 testes ancorados em literais, 5 mutações mortas, UAT real de 15/10/2026 e smoke no container.

**Issues found**: apenas bookkeeping de tasks.md (T14 checkboxes/status) — nenhuma correção de código exigida.

**Next steps**: orchestrator atualiza statuses do spec.md para Verified, marca T14 como done em tasks.md e ajusta o header de Status; pro subir a próxima feature.

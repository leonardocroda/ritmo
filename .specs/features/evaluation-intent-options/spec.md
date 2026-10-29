# Intenções de avaliação: repetição + outro

> Extensão da feature ai-evaluation (§EVAL): o seletor de intenção do formulário de avaliação ganha a opção "repetição" (zona VDOT já existe, não estava exposta) e a opção "outro" (treinos multi-habilidade ou com foco fora das zonas de ritmo — o texto livre ganha peso na interpretação do LLM, sem quebrar as comparações determinísticas do Python).

## Problem Statement

O seletor de intenção da avaliação cobre 7 tipos (fácil, tempo, limiar, intervalado, longão, progressivo, prova), mas falta:
1. **Repetição** — zona VDOT `repetition` existe e é usada na classificação das voltas, mas não há como o usuário declará-la como intenção de avaliação.
2. **Outro** — treinos que estimulam mais de uma habilidade ou têm foco diferente da zona de ritmo (ex.: técnica, progressão livre, recuperação ativa com estímulo misto) não encaixam em nenhum tipo pré-definido. O usuário precisa de uma caixa de texto que de fato influencie o veredito.

## Goals

- [ ] Adicionar "repetição" (chave `repeticao`) ao seletor de intenção, com zona alvo `["repetition"]` no payload de avaliação
- [ ] Adicionar "outro" (chave `outro`) ao seletor de intenção, sem zona alvo única (`zona_alvo` omitido), como progressivo/prova
- [ ] Quando intenção é "outro", o system prompt instrui o LLM a dar mais peso ao texto livre na interpretação da intenção, sem ignorar os números do payload (fonte da verdade continua sendo o Python)
- [ ] Nenhuma comparação do Python quebra com os novos tipos (todos os números continuam calculados da mesma forma)
- [ ] Backend aceita 9 tipos de intenção (7 originais + repeticao + outro)

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Criar nova zona VDOT | `repetition` já existe em `vdot_zones.json` e na classificação de voltas — só falta expor como intenção |
| Alterar os 5 vereditos | `on_target|too_hard|too_easy|context_explained|fatigue_signal` continuam os mesmos |
| Alterar o schema do banco | `intent_type` é `String(40)` sem constraint de enum — aceita qualquer string ASCII |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Chave ASCII para "repetição" | `repeticao` | Padrão do app: acento só na exibição, ASCII na API (mesmo que `facil`/`longao`) | y |
| Chave ASCII para "outro" | `outro` | Mesmo padrão acima | y |
| Mapeamento repetição → zona alvo | `["repetition"]` | Zona VDOT `repetition` já existe; mapeamento 1:1 com a chave da zona | y |
| Mapeamento outro → zona alvo | `None` (omitido) | Como progressivo/prova: sem zona alvo única, o LLM julga por distribuição + texto | y |
| Texto livre com "outro" | Ganha peso no prompt | O sistema prompt instrui: com "outro", a intenção declarada no texto é a fonte principal para julgar execução vs intenção | y |
| Ordem no select | repetição depois de intervalado; outro por último | Ordem do plano §4.6 estendida: fácil → tempo → limiar → intervalado → repetição → longão → progressivo → prova → outro | y |

## User Stories

### P1: Escolher "repetição" como intenção de avaliação

**User Story**: Como corredor, quero selecionar "repetição" no seletor de intenção da avaliação, para que o sistema compare minhas repetições contra a zona VDOT de repetição (não contra intervalo ou limiar).

**Acceptance Criteria**:

1. WHEN o usuário abre o formulário de avaliação THEN o select SHALL exibir "Repetição" como opção (valor `repeticao`) entre "Intervalado" e "Longão"
2. WHEN o usuário seleciona "Repetição" THEN o backend SHALL calcular `zona_alvo` com `zonas: ["repetition"]` e `pct_zona_alvo` = % de duração nas voltas classificadas como repetition

**Independent Test**: Avaliar um treino com intenção `repeticao` → `zona_alvo` presente com `["repetition"]` e percentual exato.

---

### P2: Escolher "outro" como intenção de avaliação

**User Story**: Como corredor, quero selecionar "outro" e digitar o foco do treino na caixa de texto, para que a avaliação considere minha intenção específica mesmo quando não encaixa nos tipos padrão.

**Acceptance Criteria**:

1. WHEN o usuário abre o formulário de avaliação THEN o select SHALL exibir "Outro" como opção (valor `outro`) por último
2. WHEN o usuário seleciona "Outro" THEN o backend SHALL omitir `zona_alvo` do payload (sem zona alvo única)
3. WHEN a intenção é "outro" THEN o LLM SHALL interpretar a execução contra o texto livre declarado, usando os números do payload como fonte da verdade (não recalcula, não ignora)
4. IF a intenção é "outro" e não há texto livre THEN o LLM SHALL julgar pelos agregados do payload (pace médio, zona predominante, FC) com confiança adequada

**Independent Test**: Avaliar um treino com intenção `outro` + texto → `zona_alvo` ausente; veredito reflete a intenção do texto contra os números do payload.

---

## Edge Cases

1. IF intenção é "repetição" mas não há voltas classificadas como repetition THEN `zona_alvo` tem `pct_zona_alvo: 0.0` (mesmo comportamento de intervalado sem voltas de interval)
2. IF intenção é "outro" com texto vazio THEN a avaliação prossegue com agregados + contexto, como progressivo/prova sem texto
3. IF `intent_type` for qualquer string fora dos 9 tipos THEN 422 (mesma validação dos 7 originais)
4. IF `intent_text` acima de 500 chars com "outro" THEN 422 (mesmo limite dos outros tipos)

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| EVAL-26 | P1: Escolher "repetição" | Execute | Planned |
| EVAL-27 | P2: Escolher "outro" | Execute | Planned |
| EVAL-28 | P1/P2: backend aceita 9 tipos | Execute | Planned |
| EVAL-29 | P2: texto ganha peso com "outro" | Execute | Planned |

**ID format:** `EVAL-[NUMBER]`
**Coverage:** 4 total, 4 mapped to stories, 0 unmapped

---

## Success Criteria

- [ ] Select do formulário exibe 9 opções (7 originais + Repetição + Outro), rótulos PT-BR com acento, valores ASCII
- [ ] Avaliar com `repeticao` → `zona_alvo = {"zonas": ["repetition"], "pct_zona_alvo": <exato>}`
- [ ] Avaliar com `outro` → `zona_alvo` ausente do payload; veredito considera o texto livre
- [ ] `intent_type` fora dos 9 tipos → 422
- [ ] Suite pytest verde + `npm run build`/`npm run lint` verdes

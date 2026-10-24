# Prints do site

Os prints do site público (rota `/site`, servida na raiz para visitantes
via rewrite do proxy) são da **interface real** — o build de verdade do
frontend — com **dados ilustrativos**: exemplares, coerentes entre si e
declarados como tais na página (mesma postura do doc de identidade v0.3:
"dados ilustrativos — nenhum dado real de usuário"). Nada de mockup de
imagem: a tela renderizada é a plataforma mesmo.

## Caminho mock (recomendado) — tudo automático, sem login

```bash
cd frontend
npm run build                                     # build standalone
Copy-Item -Recurse -Force .next\static .next\standalone\.next\static
Copy-Item -Recurse -Force public .next\standalone\public
$env:PORT="3100"; node .next\standalone\server.js   # preview em outra porta
RITMO_BASE=http://localhost:3100 python scripts/site/capture_mock.py
```

O script intercepta **todas** as chamadas `/api/*` pelo Playwright
(`page.route`) e entrega os payloads de uma persona exemplar: corredor
de 28 anos treinando para a Meia Best Açaí (08/11/2026), VDOT corrente
52,0 (10K 40:12) com demonstrado 54,6 (5K 18:35), veredito "Pronto pra
qualidade" e semana equilibrada. Sessão falsa no cookie — o proxy é
otimista (presença) e a API real nunca é chamada.

Os 17 prints caem em `frontend/public/prints/`:

| Arquivo | O quê |
|---|---|
| `hoje-top.png` | raiz: card-veredito, chips de sinal, strip de 7 dias |
| `hoje-abaixo.png` | abaixo da dobra: recomendações, mini de volume, digest |
| `treinos-list.png` | lista de corridas com tipos inferidos e badges |
| `treino-detail.png` | topo do detalhe do 2×3km (métricas + badges) |
| `contexto-dia.png` | seção “Contexto do dia” (chips de sono/HRV/RHR/temperatura) |
| `splits-chart.png` | card “Voltas” — largura proporcional, zonas VDOT |
| `evaluation-card.png` | card “Avaliação” — veredito da IA + auditoria |
| `performance-top.png` | linha-guia + “Onde estou” + card da lacuna |
| `performance-vdot.png` | lacuna + timeline VDOT com faixa honesta |
| `predictions.png` | previsões por método + decaimento |
| `pmc-chart.png` | curva PMC (CTL/ATL/TSB) |
| `saude-top.png` | seletor de janela + linha-guia + Sono |
| `sleep-chart.png` | sono vs piso de 7h |
| `hrv-chart.png` | HRV com banda pessoal de 60d |
| `dose-response.png` | dose-resposta do sono |
| `perfil-top.png` | conexão Garmin + seção Valores |
| `hr-zones.png` | método e zonas em bpm |

## Caminho manual — os 12 prints que o site usa

Se preferir tirar você mesmo (com seus dados): DevTools (`F12`) → device
toolbar (`Ctrl+Shift+M`) → **390×844**, DPR 2. **Print de viewport**:
`Ctrl+Shift+P` → *Capture screenshot*. **Print de card**: inspecione o
card → `Ctrl+Shift+P` → *Capture node screenshot*. Nomes e roteiro na
tabela acima (os 12 que o site referencia: hoje-top, hoje-abaixo,
treino-detail, contexto-dia, splits-chart, evaluation-card,
performance-top, performance-vdot, saude-top, dose-response, perfil-top,
hr-zones) — salve em `frontend/public/prints/` e a página se atualiza no
próximo build.

## Caminho script com sessão real

`python scripts/site/capture.py` — navegador para login manual (a senha
nunca passa pelo script), cookie fora do repo e captura dos mesmos
prints com os dados de verdade. Útil se um dia quiser o site com dados
reais (mudando a legenda da página de "ilustrativos" para "reais").

## Depois de capturar

**Rebuild do frontend** — o compose copia `public/` para dentro da
imagem no build:

```bash
docker compose up -d --build frontend
```

QA de visitante: `python scripts/site/verify_site.py` (ou
`RITMO_BASE=http://localhost:3100` para outro host/porta).

## Notas

- Se os painéis mudarem de layout, ajustam-se os seletores nos scripts
  (títulos de seção do padrão `PanelSection`) e os payloads do mock aos
  contratos de `frontend/src/lib/api.ts`.
- Os dados do mock são determinísticos (pseudo-ruído com hash fixo) —
  rodar de novo gera os mesmos prints.

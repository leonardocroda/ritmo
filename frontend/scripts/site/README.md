# Prints do site

Os prints do site público (rota `/site`, servida na raiz para visitantes
via rewrite do proxy) são **da plataforma de verdade** — capturados de uma
sessão logada com dados reais, no viewport de 390×844 (o mobile da
identidade visual v0.3), idealmente em 2× de escala.

Dois caminhos: **manual** (você tira os prints e salva com os nomes abaixo
em `frontend/public/prints/`) ou **script** (tudo automático).

## Caminho manual — os 12 prints que o site usa

Preparação (uma vez): DevTools (`F12`) → device toolbar (`Ctrl+Shift+M`) →
**390×844**, zoom 100%, device scale factor 2.

- **Print de viewport**: posicione a tela e `Ctrl+Shift+P` → *Capture
  screenshot*.
- **Print de nodo** (só o card): inspecione o card → com ele selecionado no
  Elements, `Ctrl+Shift+P` → *Capture node screenshot*.

| # | Arquivo | Rota | O que mostrar | Como |
|---|---|---|---|---|
| 1 | `hoje-top.png` | `/` | topo: card-veredito, chips de sinal, strip de 7 dias | viewport |
| 2 | `hoje-abaixo.png` | `/` | rolar a dobra: recomendações, mini de volume, digest de previsões | viewport |
| 3 | `treino-detail.png` | `/treinos/{um treino avaliado}` | topo do detalhe: título, badges, métricas | viewport |
| 4 | `contexto-dia.png` | mesmo treino | seção “Contexto do dia” (chips de sono/HRV/RHR/temperatura) | nodo |
| 5 | `splits-chart.png` | mesmo treino | card “Voltas” (gráfico por zona VDOT) | nodo |
| 6 | `evaluation-card.png` | mesmo treino | card “Avaliação” (veredito da IA) | nodo |
| 7 | `performance-top.png` | `/performance` | topo: linha-guia, seção “Onde estou”, card da lacuna | viewport |
| 8 | `performance-vdot.png` | `/performance` | seção “Onde estou” inteira (lacuna + timeline VDOT) | nodo |
| 9 | `saude-top.png` | `/saude` | topo: seletor de janela, linha-guia, seção Sono | viewport |
| 10 | `dose-response.png` | `/saude` | seção “Dose-resposta” | nodo |
| 11 | `perfil-top.png` | `/perfil` | topo: Conexão Garmin + seção Valores | viewport |
| 12 | `hr-zones.png` | `/perfil` | seção “Método e zonas” | nodo |

Depois: `git add frontend/public/prints` + commit + **rebuild do frontend**
(o compose copia `public/` para dentro da imagem no build):

```bash
docker compose up -d --build frontend
```

## Caminho script — tudo automático

```bash
cd frontend
python scripts/site/capture.py
```

O script abre um **navegador visível** em `http://localhost:3000/login` —
faça o login manualmente (a senha não passa pelo script). Quando a URL cai
num painel, o cookie de sessão é salvo em `.site-session.json` (raiz do
repo, fora do git via `.gitignore`) e o navegador fecha. Em seguida ele
captura, headless, os 12 prints acima **e mais 6 de reserva** para uso
futuro do site:

| Arquivo | O quê |
|---|---|
| `treinos-list.png` | topo de `/treinos` (lista + badges) |
| `sleep-chart.png` | card do sono vs piso de 7h |
| `hrv-chart.png` | card do HRV com banda pessoal |
| `pmc-chart.png` | curva PMC (CTL/ATL/TSB) |
| `predictions.png` | previsões por método + decaimento |
| `hr-values.png` | card de valores (FC máx/repouso/LTHR) |

## Notas

- O treino do print é escolhido via API: preferência para um com avaliação
  `done` (o card de veredito é o visual da seção de IA); fallback para o
  primeiro com voltas.
- Os prints expõem **dados reais** (nome no header, treinos, sono) para
  quem acessar o site — é o ponto do site mostrar a plataforma de verdade.
- Se os painéis mudarem de layout, ajustam-se os seletores em
  `capture.py` (títulos de seção do padrão `PanelSection`) e o checklist
  manual acima.
- QA de visitante: `python scripts/site/verify_site.py` (ou
  `RITMO_BASE=http://localhost:3100` para apontar outro host/porta).

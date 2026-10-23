# Prints do site

Os prints do site público (rota `/site`, servida na raiz para visitantes
via rewrite do proxy) são **da plataforma de verdade** — capturados de uma
sessão logada com dados reais, no viewport de 390×844 (o mobile da
identidade visual v0.3) em 2× de escala.

## Requisitos

- Stack de pé (`docker compose up -d`) — o frontend precisa estar em `:3000`
  e o login precisa funcionar.
- Playwright Python: `pip install playwright` (browsers: `python -m
  playwright install chromium`).

## Capturar

```bash
cd frontend
python scripts/site/capture.py
```

O script abre um **navegador visível** em `http://localhost:3000/login` —
faça o login manualmente (a senha não passa pelo script). Quando a URL cair
num painel, o cookie de sessão é salvo em `.site-session.json` (raiz do repo,
fora do git via `.gitignore`) e o navegador fecha. Em seguida ele captura,
headless:

| Arquivo | O quê |
|---|---|
| `treinos-list.png` | topo de `/treinos` (lista + badges) |
| `treino-detail.png` | topo do detalhe do treino avaliado |
| `splits-chart.png` | card do gráfico de voltas (zonas VDOT) |
| `evaluation-card.png` | card de veredito da IA |
| `contexto-dia.png` | faixa de contexto (sono, HRV, RHR, temperatura) |
| `performance-top.png` | topo de `/performance` (linha-guia + lacuna) |
| `performance-vdot.png` | card da lacuna + timeline VDOT |
| `predictions.png` | previsões por método + decaimento |
| `pmc-chart.png` | curva PMC (CTL/ATL/TSB) |
| `saude-top.png` | topo de `/saude` |
| `sleep-chart.png` | sono vs piso de 7h |
| `hrv-chart.png` | HRV com banda pessoal |
| `dose-response.png` | dose-resposta do sono |
| `perfil-top.png` | topo de `/perfil` (conexão + valores) |
| `hr-values.png` | card de valores (FC máx/repouso/LTHR) |
| `hr-zones.png` | método + zonas em bpm |

Os PNGs caem em `frontend/public/prints/` e o site os referencia como
`/prints/<arquivo>`. Depois de re-capturar, **rebuild do frontend** (o compose
copia `public/` para dentro da imagem no build):

```bash
docker compose up -d --build frontend
```

## Notas

- O treino do print é escolhido via API: preferência para um com avaliação
  `done` (o card de veredito é o visual da seção de IA); fallback para o
  primeiro com voltas.
- Os prints expõem **dados reais** (nome no header, treinos, sono) para
  quem acessar o site — é o ponto do site mostrar a plataforma de verdade.
- Se os painéis mudarem de layout, ajustem-se os seleções em
  `capture.py` (títulos de seção do padrão `PanelSection`).

"use client";

// Gráfico de splits (TRN-16/17/18) — SVG próprio, port do renderer
// validado (generate_image.py): largura da barra PROPORCIONAL à duração
// da volta (uma pausa de 30s não pode ter o tamanho de um tiro de 3km —
// decisão do usuário), altura por pace clampado a [180, 420] s/km com
// piso de 2.5 (recuperação fica no fundo, sem barra negativa), linha de
// FC com ponto no MEIO de cada barra e relevo atrás em eixo próprio.
// Sem Recharts: o eixo categórico da lib daria slots iguais (design).
// Todas as cores (zonas e FC) vêm do payload — backend é a fonte única.
// ViewBox no tamanho do alvo mobile: em telas maiores o gráfico escala
// para cima em vez de encolher fontes no 390px.

import { useState } from "react";

import type { SplitOut, ZoneMeta } from "@/lib/api";
import { formatDuration, formatPace } from "@/lib/format";

const W = 390;
const H = 268;
// Margens comportam os eixos rotulados (UAT 15/10/2026): ritmo à esquerda,
// FC à direita — bater o olho e ler o gráfico sem consulta mental.
const MARGIN = { top: 14, right: 30, bottom: 26, left: 34 };
const PLOT_W = W - MARGIN.left - MARGIN.right; // 370
const PLOT_H = H - MARGIN.top - MARGIN.bottom; // 228
const PLOT_BOTTOM = MARGIN.top + PLOT_H;

// Escala de pace (s/km): 3:00/km -> barra cheia; 7:00/km ou mais -> no chão
const PACE_MIN_S = 180;
const PACE_MAX_S = 420;
const MIN_BAR_H = 2.5;

// Rótulos: pace só quando a barra comporta o texto; km com espaçamento mínimo
const PACE_LABEL_MIN_W = 26;
const KM_LABEL_GAP = 34;

// Banda de relevo: eixo próprio, até 35% da altura útil
const ELEV_BAND_H = PLOT_H * 0.35;

const AXIS_COLOR = "#3f3f46";
const TEXT_COLOR = "#d4d4d8";
const MUTED_COLOR = "#a1a1aa";

type Props = {
  splits: SplitOut[];
  zones: ZoneMeta[];
  hrColor: string;
};

type Bar = {
  split: SplitOut;
  x: number;
  width: number;
  midX: number;
  /** Altura da barra de pace (null = volta sem pace válido: sem barra). */
  barH: number | null;
};

function Legend({
  zonesPresent,
  hrColor,
}: {
  zonesPresent: ZoneMeta[];
  hrColor: string;
}) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
      {zonesPresent.map((zone) => (
        <span key={zone.key} className="flex items-center gap-1.5" title={zone.pace_range}>
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm"
            style={{ backgroundColor: zone.color }}
          />
          {zone.label}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span
          aria-hidden
          className="inline-block h-0.5 w-4"
          style={{ backgroundColor: hrColor }}
        />
        FC
      </span>
    </div>
  );
}

function kmAnchor(x: number): "start" | "middle" | "end" {
  if (x > W - MARGIN.right - 14) return "end";
  if (x < MARGIN.left + 14) return "start";
  return "middle";
}

/** Distância da volta no tooltip (UAT 15/10/2026): "800 m" / "1,0 km". */
function formatLapDistance(distM: number | null): string {
  if (distM === null) return "—";
  if (distM >= 995) return `${(distM / 1000).toFixed(1).replace(".", ",")} km`;
  return `${Math.round(distM)} m`;
}

export default function SplitsChart({ splits, zones, hrColor }: Props) {
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  const zoneByKey = new Map<string, ZoneMeta>(zones.map((zone) => [zone.key, zone]));
  const zonesPresent = zones.filter((zone) =>
    splits.some((split) => split.zone === zone.key),
  );

  // Volta com pace válido (distância e duração > 0) gera barra (spec)
  const hasAnyPace = splits.some((split) => split.zone !== null);
  const timed = splits.filter((split) => split.duration_s !== null && split.duration_s > 0);
  const totalDuration = timed.reduce((sum, split) => sum + (split.duration_s ?? 0), 0);

  if (!hasAnyPace || totalDuration <= 0) {
    // Edge do spec: todas as voltas sem pace válido -> eixo vazio + nota
    return (
      <div>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full"
          role="img"
          aria-label="Gráfico de splits sem voltas com pace válido"
        >
          <line
            x1={MARGIN.left}
            x2={W - MARGIN.right}
            y1={PLOT_BOTTOM}
            y2={PLOT_BOTTOM}
            stroke={AXIS_COLOR}
          />
          <text
            x={W / 2}
            y={MARGIN.top + PLOT_H / 2}
            textAnchor="middle"
            fontSize={11}
            fill={MUTED_COLOR}
          >
            sem voltas com pace
          </text>
        </svg>
        <Legend zonesPresent={[]} hrColor={hrColor} />
      </div>
    );
  }

  // Geometria: TODA volta com duração consome largura proporcional à sua
  // duração na área útil; só as com pace válido ganham barra (pausa sem
  // pace ainda ocupa o lugar dela na linha do tempo).
  const bars: Bar[] = timed.reduce<Bar[]>((acc, split) => {
    const width = PLOT_W * ((split.duration_s ?? 0) / totalDuration);
    const previous = acc[acc.length - 1];
    const x = previous !== undefined ? previous.x + previous.width : MARGIN.left;
    let barH: number | null = null;
    if (split.zone !== null && split.pace_s !== null) {
      // Clamp [180, 420] s/km com piso de 2.5 (port do validado): pace
      // fora da escala vira barra no extremo, nunca negativa/invisível
      const clamped = Math.min(PACE_MAX_S, Math.max(PACE_MIN_S, split.pace_s));
      barH = Math.max(
        MIN_BAR_H,
        (1 - (clamped - PACE_MIN_S) / (PACE_MAX_S - PACE_MIN_S)) * PLOT_H,
      );
    }
    return [...acc, { split, x, width, midX: x + width / 2, barH }];
  }, []);

  // Relevo atrás em eixo próprio: escala pela maior subida de volta
  const elevMax = Math.max(
    0,
    ...splits
      .map((split) => split.elevation_m ?? 0)
      .filter((elev) => elev > 0),
  );

  // Linha de FC: ponto no meio de cada barra, na cor reservada do payload;
  // voltas sem FC ficam fora da linha — ela conecta os pontos existentes
  const hrBars = bars.filter((bar) => bar.split.avg_hr !== null);
  const hrValues = hrBars.map((bar) => bar.split.avg_hr as number);
  const hrMin = Math.min(...hrValues);
  const hrMax = Math.max(...hrValues);
  const hrRange = hrMax - hrMin || 1;
  const hrY = (hr: number) => MARGIN.top + (1 - (hr - hrMin) / hrRange) * PLOT_H;
  const hrPolyline = hrBars
    .map((bar) => `${bar.midX},${hrY(bar.split.avg_hr as number)}`)
    .join(" ");

  // Eixo X: km acumulado nas marcas proporcionais (km_label do payload é
  // o acumulado no FIM da volta); espaçamento mínimo evita poluição
  const kmLabels: { x: number; text: string }[] = bars.reduce<{ x: number; text: string }[]>(
    (acc, bar, index) => {
      const boundary = bar.x + bar.width;
      const lastX = acc.length > 0 ? acc[acc.length - 1].x : MARGIN.left;
      if (index === bars.length - 1 || boundary - lastX >= KM_LABEL_GAP) {
        return [...acc, { x: boundary, text: bar.split.km_label }];
      }
      return acc;
    },
    [],
  );

  const active = activeIdx !== null ? bars[activeIdx] : null;

  // Eixo Y esquerdo: pace com ticks a cada 60s (3:00–7:00), mesma escala
  // das barras — clamp included (7:00 fica no chão). Gridlines sutis.
  const paceTicks = [180, 240, 300, 360, 420];
  const paceTickY = (paceS: number) =>
    MARGIN.top + ((paceS - PACE_MIN_S) / (PACE_MAX_S - PACE_MIN_S)) * PLOT_H;

  // Eixo Y direito: FC com ticks min/meio/máx da escala da linha (valores
  // reais presentes nos dados); degenerado (FC única) mostra só um tick.
  const hrMid = Math.round((hrMin + hrMax) / 2);
  const hrTicks =
    hrMin === hrMax
      ? [{ hr: hrMin, y: hrY(hrMin) }]
      : [
          { hr: hrMax, y: hrY(hrMax) },
          { hr: hrMid, y: hrY(hrMid) },
          { hr: hrMin, y: hrY(hrMin) },
        ];

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label="Gráfico de splits: pace por volta colorido por zona VDOT, com FC e relevo"
      >
        {/* Eixos rotulados (UAT): gridlines de pace atrás dos dados,
            ritmo à esquerda, FC à direita */}
        {paceTicks.map((paceS) => (
          <line
            key={`grid-${paceS}`}
            x1={MARGIN.left}
            x2={W - MARGIN.right}
            y1={paceTickY(paceS)}
            y2={paceTickY(paceS)}
            stroke={AXIS_COLOR}
            strokeOpacity={0.35}
          />
        ))}
        {paceTicks.map((paceS) => (
          <text
            key={`ptick-${paceS}`}
            x={MARGIN.left - 4}
            y={paceTickY(paceS) + 3}
            textAnchor="end"
            fontSize={8}
            fill={MUTED_COLOR}
          >
            {formatPace(paceS)}
          </text>
        ))}
        {hrBars.length > 0 &&
          hrTicks.map((tick) => (
            <text
              key={`htick-${tick.hr}`}
              x={W - MARGIN.right + 4}
              y={tick.y + 3}
              textAnchor="start"
              fontSize={8}
              fill={hrColor}
            >
              {`${tick.hr}`}
            </text>
          ))}

        {/* Relevo atrás (eixo próprio) */}
        {elevMax > 0 &&
          bars.map((bar) => {
            const elev = bar.split.elevation_m ?? 0;
            if (elev <= 0) return null;
            const elevH = Math.min(ELEV_BAND_H, (elev / elevMax) * ELEV_BAND_H);
            return (
              <rect
                key={`elev-${bar.split.idx}`}
                x={bar.x}
                y={PLOT_BOTTOM - elevH}
                width={bar.width}
                height={elevH}
                fill={MUTED_COLOR}
                fillOpacity={0.18}
              />
            );
          })}

        {/* Barras de pace por zona (largura = duração da volta) */}
        {bars.map((bar) =>
          bar.barH !== null ? (
            <rect
              key={`bar-${bar.split.idx}`}
              x={bar.x}
              y={PLOT_BOTTOM - bar.barH}
              width={bar.width}
              height={bar.barH}
              fill={zoneByKey.get(bar.split.zone as string)?.color ?? MUTED_COLOR}
            />
          ) : null,
        )}

        {/* Rótulo de pace — oculto quando a barra é estreita demais */}
        {bars.map((bar) =>
          bar.barH !== null && bar.width >= PACE_LABEL_MIN_W ? (
            <text
              key={`pace-${bar.split.idx}`}
              x={bar.midX}
              y={PLOT_BOTTOM - bar.barH - 5}
              textAnchor="middle"
              fontSize={9}
              fill={TEXT_COLOR}
            >
              {formatPace(bar.split.pace_s as number)}
            </text>
          ) : null,
        )}

        {/* Linha de FC (cor do payload, distinta de todas as zonas) */}
        {hrBars.length > 0 && (
          <polyline
            points={hrPolyline}
            fill="none"
            stroke={hrColor}
            strokeWidth={1.5}
          />
        )}
        {hrBars.map((bar) => (
          <circle
            key={`hr-${bar.split.idx}`}
            cx={bar.midX}
            cy={hrY(bar.split.avg_hr as number)}
            r={2}
            fill={hrColor}
          />
        ))}

        {/* Eixo X: linha base + km acumulado nas marcas proporcionais */}
        <line
          x1={MARGIN.left}
          x2={W - MARGIN.right}
          y1={PLOT_BOTTOM}
          y2={PLOT_BOTTOM}
          stroke={AXIS_COLOR}
        />
        {kmLabels.map((label) => (
          <g key={`km-${label.x}`}>
            <line
              x1={label.x}
              x2={label.x}
              y1={PLOT_BOTTOM}
              y2={PLOT_BOTTOM + 3}
              stroke={AXIS_COLOR}
            />
            <text
              x={label.x}
              y={H - 8}
              textAnchor={kmAnchor(label.x)}
              fontSize={9}
              fill={MUTED_COLOR}
            >
              {label.text}
            </text>
          </g>
        ))}

        {/* Tooltip por hover/tap — pace REAL (não clampado), FC, elevação,
            duração, distância da volta e zona */}
        {active !== null && (
          <g>
            <rect
              x={Math.min(Math.max(active.midX + 8, 4), W - 116)}
              y={MARGIN.top + 2}
              width={112}
              height={89}
              rx={6}
              fill="#18181b"
              fillOpacity={0.95}
              stroke={AXIS_COLOR}
            />
            <text
              x={Math.min(Math.max(active.midX + 8, 4), W - 116) + 8}
              y={MARGIN.top + 15}
              fontSize={10}
              fill="#ffffff"
            >
              {`Volta ${active.split.idx} · ${active.split.km_label} km`}
            </text>
            {[
              `pace: ${active.split.pace_s !== null ? `${formatPace(active.split.pace_s)}/km` : "—"}`,
              `volta: ${formatLapDistance(active.split.dist_m)}`,
              `FC: ${active.split.avg_hr !== null ? `${active.split.avg_hr} bpm` : "—"}`,
              `elev: ${active.split.elevation_m !== null ? `${active.split.elevation_m.toFixed(1).replace(".", ",")} m` : "—"}`,
              `duração: ${active.split.duration_s !== null ? formatDuration(active.split.duration_s) : "—"}`,
              `zona: ${active.split.zone !== null ? (zoneByKey.get(active.split.zone)?.label ?? active.split.zone) : "—"}`,
            ].map((line, lineIndex) => (
              <text
                key={line}
                x={Math.min(Math.max(active.midX + 8, 4), W - 116) + 8}
                y={MARGIN.top + 28 + lineIndex * 11}
                fontSize={10}
                fill={TEXT_COLOR}
              >
                {line}
              </text>
            ))}
          </g>
        )}

        {/* Hit-areas: fatia inteira de cada volta (barras de 100m ficam
            tocáveis) — hover/tap trocam a volta ativa */}
        {bars.map((bar, index) => (
          <rect
            key={`hit-${bar.split.idx}`}
            x={bar.x}
            y={MARGIN.top}
            width={bar.width}
            height={PLOT_H}
            fill="transparent"
            onMouseEnter={() => setActiveIdx(index)}
            onMouseLeave={() => setActiveIdx((prev) => (prev === index ? null : prev))}
            onClick={() =>
              setActiveIdx((prev) => (prev === index ? null : index))
            }
          />
        ))}
      </svg>
      <Legend zonesPresent={zonesPresent} hrColor={hrColor} />
    </div>
  );
}

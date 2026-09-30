import type { ChartData } from "@/lib/content";

/** Series colours in fixed order (tokens in globals.css, validated for both themes). */
export const SERIES = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];

/** A long category label broken at the word boundary nearest its middle. */
function twoLines(label: string): string[] {
  if (label.length <= 14 || !label.includes(" ")) return [label];
  const words = label.split(" ");
  let best = 1;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(" ").length;
    const b = words.slice(0, best).join(" ").length;
    if (Math.abs(a - label.length / 2) < Math.abs(b - label.length / 2)) best = i;
  }
  return [words.slice(0, best).join(" "), words.slice(best).join(" ")];
}

const fmt = (v: unknown) => (v === null || v === undefined ? "—" : String(v));

/** Axis titles and legends come from the book with light markup ("K<sub>i</sub>"); plain for aria/titles. */
export const plain = (s: string | null | undefined) => (s ?? "").replace(/<[^>]+>/g, "").replace(/\*/g, "");

/** The same text as HTML (titles, legend): markup kept, *italic* as <em>. */
export const richHtml = (s: string | null | undefined) => ({ __html: (s ?? "").replace(/\*([^*]+)\*/g, "<em>$1</em>") });

/** The same text for SVG: <sub>/<sup> become shifted tspans, *italic* becomes an italic tspan. */
export function SvgText({ text }: { text: string | null | undefined }) {
  const parts = (text ?? "").split(/(<sub>.*?<\/sub>|<sup>.*?<\/sup>|\*[^*]+\*)/g).filter(Boolean);
  return (
    <>
      {parts.map((p, i) => {
        const inner = p.replace(/<[^>]+>/g, "").replace(/\*/g, "");
        if (p.startsWith("<sub>")) return <tspan key={i} baselineShift="sub" fontSize="0.75em">{inner}</tspan>;
        if (p.startsWith("<sup>")) return <tspan key={i} baselineShift="super" fontSize="0.75em">{inner}</tspan>;
        if (p.startsWith("*")) return <tspan key={i} fontStyle="italic">{inner}</tspan>;
        return <tspan key={i}>{inner}</tspan>;
      })}
    </>
  );
}

export function Legend({ chart, marker = "bar" }: { chart: ChartData; marker?: "bar" | "line" }) {
  if (chart.series.length < 2) return null;
  return (
    <ul className="mt-2 flex flex-wrap justify-center gap-x-5 gap-y-1 text-meta text-ink-soft" aria-hidden>
      {chart.series.map((s, j) => (
        <li key={s.key} className="flex items-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            {marker === "bar" ? (
              <rect x="1" y="1" width="12" height="12" rx="2" fill={SERIES[j % SERIES.length]} />
            ) : (
              <>
                <line x1="0" x2="14" y1="7" y2="7" stroke={SERIES[j % SERIES.length]} strokeWidth="2" />
                <Marker shape={j} x={7} y={7} color={SERIES[j % SERIES.length]} />
              </>
            )}
          </svg>
          <span dangerouslySetInnerHTML={richHtml(s.en)} />
        </li>
      ))}
    </ul>
  );
}

/** Different marker shapes per series, so identity never rests on colour alone. */
export function Marker({ shape, x, y, color }: { shape: number; x: number; y: number; color: string }) {
  const r = 4.5;
  const common = { fill: color, stroke: "var(--paper)", strokeWidth: 1.5 };
  switch (shape % 4) {
    case 1:
      return <rect x={x - r} y={y - r} width={r * 2} height={r * 2} {...common} />;
    case 2:
      return <polygon points={`${x},${y - r - 1} ${x + r + 1},${y + r} ${x - r - 1},${y + r}`} {...common} />;
    case 3:
      return <polygon points={`${x},${y - r - 1} ${x + r + 1},${y} ${x},${y + r + 1} ${x - r - 1},${y}`} {...common} />;
    default:
      return <circle cx={x} cy={y} r={r} {...common} />;
  }
}

/** The values as a table for screen readers (and anyone who wants the numbers). */
export function DataTable({ chart }: { chart: ChartData }) {
  const cats = chart.categories ?? [];
  return (
    // A table ignores the 1px box of sr-only, so the wrapper carries it.
    <div className="sr-only">
      <table>
        <caption>{plain(chart.title.en)}</caption>
        <thead>
          <tr>
            <th scope="col">{plain(chart.x_axis?.en) || "Category"}</th>
            {chart.series.map((s) => (
              <th key={s.key} scope="col">{plain(s.en)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cats.map((cat) => (
            <tr key={cat.en}>
              <th scope="row">{cat.en}</th>
              {chart.series.map((s) => (
                <td key={s.key}>{fmt(cat[s.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Grouped bar chart redrawn from the book's values (figures/charts/*.yaml).
 * Pure SVG in theme tokens; printed values are shown as in the book; a data table follows for screen readers.
 */
export function BarChart({ chart }: { chart: ChartData }) {
  const cats = chart.categories ?? [];
  const many = cats.length > 30; // e.g. one bar per year: label every 5th
  const rotate = !many && cats.length > 8; // few categories wrap onto two lines instead
  const width = 640;
  const bottom = many ? 44 : rotate ? 96 : 52;
  const margin = { top: 22, right: 12, bottom: bottom + (chart.x_axis ? 18 : 0), left: chart.y_axis.en ? 62 : 44 };
  const height = 300 + (rotate ? 44 : 0);
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const { min, max, ticks } = chart.y_axis;
  const y = (v: number) => margin.top + plotH - ((v - min) / (max - min)) * plotH;

  const groupW = plotW / cats.length;
  const barW = Math.min(30, (groupW * 0.78) / chart.series.length);
  const labelValues = chart.values_printed && barW >= 9;

  return (
    <figure className="font-sans">
      {plain(chart.title.en) && <p className="mb-2 text-center text-note font-semibold text-balance text-ink" dangerouslySetInnerHTML={richHtml(chart.title.en)} />}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        role="img"
        aria-label={`${plain(chart.title.en) || "Chart"}. Bar chart; the values are in the table that follows.`}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line x1={margin.left} x2={width - margin.right} y1={y(t)} y2={y(t)} stroke="var(--rule)" />
            <text x={margin.left - 7} y={y(t)} dy="0.32em" textAnchor="end" fontSize="11.5" fill="var(--ink-faint)">
              {t}
            </text>
          </g>
        ))}
        {chart.y_axis.en && (
          <text
            transform={`translate(14 ${margin.top + plotH / 2}) rotate(-90)`}
            textAnchor="middle"
            fontSize="12"
            fill="var(--ink-soft)"
          >
            <SvgText text={chart.y_axis.en} />
          </text>
        )}
        {cats.map((cat, i) => {
          const cx = margin.left + groupW * i + groupW / 2;
          const start = cx - (barW * chart.series.length) / 2;
          // Many bars (one per year): label round years only; the book's axis isn't linear before 1984.
          const showLabel = !many || (/^\d{4}$/.test(cat.en) ? Number(cat.en) % 5 === 0 : i % 5 === 0);
          return (
            <g key={`${cat.en}-${i}`}>
              {chart.series.map((s, j) => {
                const raw = cat[s.key];
                if (raw === null || raw === undefined) return null;
                const v = Number(raw);
                const top = y(Math.max(min, Math.min(max, v)));
                return (
                  <g key={s.key}>
                    <rect
                      x={start + j * barW + 1}
                      y={top}
                      width={barW - 2}
                      height={Math.max(0, y(min) - top)}
                      fill={SERIES[j % SERIES.length]}
                      rx={Math.min(3, barW / 4)}
                    >
                      <title>{`${plain(s.en)}, ${cat.en}: ${fmt(raw)}`}</title>
                    </rect>
                    {labelValues && (
                      <text
                        x={start + j * barW + barW / 2}
                        y={top - 4}
                        textAnchor="middle"
                        fontSize={barW < 16 ? 8.5 : 10.5}
                        fill="var(--ink-soft)"
                      >
                        {fmt(raw)}
                      </text>
                    )}
                  </g>
                );
              })}
              {showLabel &&
                (rotate || many ? (
                  <text
                    transform={`translate(${cx} ${y(min) + 12}) rotate(${many ? -90 : -40})`}
                    textAnchor="end"
                    dy={many ? "0.32em" : undefined}
                    fontSize="11"
                    fill="var(--ink-soft)"
                  >
                    {cat.en}
                  </text>
                ) : (
                  <text x={cx} y={y(min) + 18} textAnchor="middle" fontSize="12" fill="var(--ink-soft)">
                    {twoLines(cat.en).map((line, k) => (
                      <tspan key={k} x={cx} dy={k ? "1.2em" : undefined}>
                        {line}
                      </tspan>
                    ))}
                  </text>
                ))}
            </g>
          );
        })}
        <line x1={margin.left} x2={width - margin.right} y1={y(min)} y2={y(min)} stroke="var(--ink-faint)" />
        {chart.x_axis?.en && (
          <text x={margin.left + plotW / 2} y={height - 6} textAnchor="middle" fontSize="12" fill="var(--ink-soft)">
            <SvgText text={chart.x_axis.en} />
          </text>
        )}
      </svg>
      <Legend chart={chart} />
      <DataTable chart={chart} />
    </figure>
  );
}

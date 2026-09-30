import type { ChartData } from "@/lib/content";
import { Legend, Marker, SERIES, SvgText, plain, richHtml } from "@/components/bar-chart";

/**
 * Line chart (e.g. dose–response curves) redrawn from values measured off the printed chart.
 * One marker shape per series, 2px lines, a table of the points for screen readers.
 */
export function LineChart({ chart }: { chart: ChartData }) {
  const x_axis = chart.x_axis!;
  const width = 640;
  const height = 320;
  const margin = { top: 16, right: 14, bottom: 52, left: chart.y_axis.en ? 62 : 44 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  // Half a step of room at both ends, so the first and last points don't sit on the plot edge.
  const pad = ((x_axis.max! - x_axis.min!) / Math.max(1, (x_axis.ticks?.length ?? 2) - 1)) / 2;
  const x = (v: number) => margin.left + ((v - x_axis.min! + pad) / (x_axis.max! - x_axis.min! + 2 * pad)) * plotW;
  const y = (v: number) => margin.top + plotH - ((v - chart.y_axis.min) / (chart.y_axis.max - chart.y_axis.min)) * plotH;
  const points = chart.points ?? {};

  return (
    <figure className="font-sans">
      {plain(chart.title.en) && <p className="mb-2 text-center text-note font-semibold text-balance text-ink" dangerouslySetInnerHTML={richHtml(chart.title.en)} />}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        role="img"
        aria-label={`${plain(chart.title.en) || "Chart"}. Line chart; the values are in the table that follows.`}
      >
        {chart.y_axis.ticks.map((t) => (
          <g key={`y${t}`}>
            <line x1={margin.left} x2={width - margin.right} y1={y(t)} y2={y(t)} stroke="var(--rule)" />
            <text x={margin.left - 7} y={y(t)} dy="0.32em" textAnchor="end" fontSize="11.5" fill="var(--ink-faint)">
              {t}
            </text>
          </g>
        ))}
        {(x_axis.ticks ?? []).map((t) => (
          <text key={`x${t}`} x={x(t)} y={margin.top + plotH + 18} textAnchor="middle" fontSize="11.5" fill="var(--ink-faint)">
            {t}
          </text>
        ))}
        <line x1={margin.left} x2={width - margin.right} y1={y(chart.y_axis.min)} y2={y(chart.y_axis.min)} stroke="var(--ink-faint)" />
        {chart.y_axis.en && (
          <text transform={`translate(14 ${margin.top + plotH / 2}) rotate(-90)`} textAnchor="middle" fontSize="12" fill="var(--ink-soft)">
            <SvgText text={chart.y_axis.en} />
          </text>
        )}
        {x_axis.en && (
          <text x={margin.left + plotW / 2} y={height - 8} textAnchor="middle" fontSize="12" fill="var(--ink-soft)">
            <SvgText text={x_axis.en} />
          </text>
        )}
        {chart.series.map((s, j) => {
          const pts = points[s.key] ?? [];
          const color = SERIES[j % SERIES.length];
          return (
            <g key={s.key}>
              <polyline
                points={pts.map(([px, py]) => `${x(px)},${y(py)}`).join(" ")}
                fill="none"
                stroke={color}
                strokeWidth="2"
                strokeLinejoin="round"
              />
              {pts.map(([px, py]) => (
                <g key={`${px}-${py}`}>
                  <Marker shape={j} x={x(px)} y={y(py)} color={color} />
                  {/* A larger invisible target, so the hover title is easy to hit. */}
                  <circle cx={x(px)} cy={y(py)} r="9" fill="transparent">
                    <title>{`${plain(s.en)}: ${px} → ${py}`}</title>
                  </circle>
                </g>
              ))}
            </g>
          );
        })}
      </svg>
      <Legend chart={chart} marker="line" />
      <div className="sr-only">
        <table>
          <caption>{plain(chart.title.en)}</caption>
          <thead>
            <tr>
              <th scope="col">Series</th>
              <th scope="col">{plain(x_axis.en) || "x"}</th>
              <th scope="col">{plain(chart.y_axis.en) || "y"}</th>
            </tr>
          </thead>
          <tbody>
            {chart.series.flatMap((s) =>
              (points[s.key] ?? []).map(([px, py]) => (
                <tr key={`${s.key}-${px}`}>
                  <th scope="row">{plain(s.en)}</th>
                  <td>{px}</td>
                  <td>{py}</td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

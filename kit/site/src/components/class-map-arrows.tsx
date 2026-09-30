"use client";

import { useEffect, useRef, useState } from "react";
import { SvgText } from "@/components/bar-chart";

type Arrow = {
  x: number;
  y: number;
  angle: number;
  len: number;
  label: string;
  lx: number;
  ly: number;
};

/** Where a ray from the centre of box b in direction (dx, dy) leaves the box (grown by pad). */
function exit(
  b: DOMRect,
  cx: number,
  cy: number,
  dx: number,
  dy: number,
  pad: number,
) {
  const hx = b.width / 2 + pad;
  const hy = b.height / 2 + pad;
  const t = Math.min(
    dx ? hx / Math.abs(dx) : Infinity,
    dy ? hy / Math.abs(dy) : Infinity,
  );
  return { x: cx + dx * t, y: cy + dy * t };
}

/**
 * The class map's open arrows, drawn on the true line from the parent structure to each class (measured after
 * layout, redrawn on resize). Cells are marked data-cm="core" / data-cm="class" by SchemeView.
 */
export function ClassMapArrows() {
  const ref = useRef<SVGSVGElement>(null);
  const [arrows, setArrows] = useState<Arrow[]>([]);

  useEffect(() => {
    const svg = ref.current;
    const box = svg?.parentElement;
    if (!svg || !box) return;
    const measure = () => {
      const origin = box.getBoundingClientRect();
      // Measured rectangles include any zoom/transform on an ancestor (a figure scaled to fit a printed page);
      // the SVG draws in the box's own, unscaled coordinates.
      const k = box.offsetWidth ? origin.width / box.offsetWidth : 1;
      const core = box
        .querySelector('[data-cm="core"] .structure')
        ?.getBoundingClientRect();
      // Hidden (phones get the card list): nothing to measure.
      if (!core || core.width === 0 || origin.width === 0) return setArrows([]);
      const cx = core.left + core.width / 2;
      const cy = core.top + core.height / 2;
      const next: Arrow[] = [];
      box.querySelectorAll<HTMLElement>('[data-cm="class"]').forEach((cell) => {
        const dir = cell.dataset.arrow;
        if (dir !== "out" && dir !== "in") return;
        // Aim at the class's structure, not the callout text beside it.
        const b = (cell.querySelector(".structure") ?? cell).getBoundingClientRect();
        const tx = b.left + b.width / 2;
        const ty = b.top + b.height / 2;
        const d = Math.hypot(tx - cx, ty - cy);
        if (!d || b.width === 0) return;
        const dx = (tx - cx) / d;
        const dy = (ty - cy) / d;
        const from = exit(core, cx, cy, dx, dy, 10);
        const to = exit(b, tx, ty, -dx, -dy, 8);
        const gap = Math.hypot(to.x - from.x, to.y - from.y);
        if (gap / k < 24) return;
        const len = Math.min(64, gap / k);
        const x = ((from.x + to.x) / 2 - origin.left) / k;
        const y = ((from.y + to.y) / 2 - origin.top) / k;
        // Label beside the arrow: on the upper side (the right side for a vertical arrow), clear of the shaft.
        let nx = -dy;
        let ny = dx;
        if (ny > 0.01 || (Math.abs(ny) <= 0.01 && nx < 0))
          [nx, ny] = [-nx, -ny];
        next.push({
          x,
          y,
          angle:
            (Math.atan2(dy, dx) * 180) / Math.PI + (dir === "in" ? 180 : 0),
          len,
          label: cell.dataset.label ?? "",
          lx: x + nx * 18,
          ly: y + ny * 18,
        });
      });
      setArrows(next);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(box);
    return () => ro.disconnect();
  }, []);

  return (
    <svg
      ref={ref}
      className="pointer-events-none absolute inset-0 h-full w-full overflow-visible text-ink-soft"
      aria-hidden
    >
      {arrows.map((a, i) => {
        const h = a.len / 2;
        // The book's hollow block arrow, from the parent structure to the class (or back, "in").
        return (
          <g key={i}>
            {a.label && (
              <text
                x={a.lx}
                y={a.ly}
                textAnchor={
                  Math.abs(a.lx - a.x) < 4
                    ? "middle"
                    : a.lx > a.x
                      ? "start"
                      : "end"
                }
                dominantBaseline="middle"
                fontSize="12"
                className="fill-current font-sans"
              >
                <SvgText text={a.label} />
              </text>
            )}
            <polygon
              transform={`translate(${a.x} ${a.y}) rotate(${a.angle})`}
              points={`${-h},-4 ${h - 10},-4 ${h - 10},-10 ${h},0 ${h - 10},10 ${h - 10},4 ${-h},4`}
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
          </g>
        );
      })}
    </svg>
  );
}

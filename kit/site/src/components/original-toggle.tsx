"use client";

import { useState } from "react";

/** Shows the printed original of a redrawn figure or a transcribed table, for comparison. With the figure's id
 * underneath (quietly, once open): the handle to search for it or refer to it. */
export function OriginalToggle({ src, width, height, alt, id }: { src: string; width: number; height: number; alt: string; id?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-3 font-sans">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="inline-flex min-h-9 items-center gap-1.5 rounded-sm px-2 text-meta text-ink-faint transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-accent aria-expanded:text-accent"
      >
        <span aria-hidden className={`transition-transform duration-200 ease-out-soft ${open ? "rotate-90" : ""}`}>
          ›
        </span>
        {open ? "Hide printed original" : "Compare with printed original"}
      </button>
      {open && (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP */}
          <img
            src={src}
            width={width}
            height={height}
            alt={alt}
            loading="lazy"
            className="mt-2 h-auto w-full rounded-sm border border-rule scan"
          />
          {id && <p className="mt-1.5 text-right text-meta tabular-nums text-ink-faint select-all">{id}</p>}
        </>
      )}
    </div>
  );
}

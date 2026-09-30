"use client";

import BOOK from "@/book.json";
import { useState } from "react";

/**
 * Reveals the German original of one block. The panel it controls is rendered
 * by the server next to the English text; this only flips `data-open` on it.
 */
export function GermanToggle({ panelId, page }: { panelId: string; page: number | string | null }) {
  const [open, setOpen] = useState(false);

  function toggle() {
    const next = !open;
    setOpen(next);
    document.getElementById(panelId)?.toggleAttribute("data-open", next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-expanded={open}
      aria-controls={panelId}
      title={open ? `Hide the ${BOOK.source.name} original` : `Show the ${BOOK.source.name} original`}
      className="group inline-flex h-7 min-w-11 items-center justify-center gap-1 rounded-sm px-1.5 font-sans text-meta text-ink-faint transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-accent aria-expanded:bg-accent-soft aria-expanded:text-accent"
    >
      <span className="font-semibold tracking-wide">{BOOK.source.short}</span>
      {page !== null && <span className="sr-only">, page {page}</span>}
    </button>
  );
}

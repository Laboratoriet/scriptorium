"use client";

import { useEffect, useState } from "react";

export const NOTES_KEY = "notes-hidden";

/** Hides or shows the translator's notes (margin notes, their inline versions and the markers in the text).
 * A reading preference, so it's remembered across visits; the layout applies it before first paint. */
export function ShowNotes() {
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    setHidden(document.documentElement.hasAttribute("data-notes-hidden"));
  }, []);

  function toggle() {
    const next = !hidden;
    setHidden(next);
    document.documentElement.toggleAttribute("data-notes-hidden", next);
    try { localStorage.setItem(NOTES_KEY, next ? "1" : "0"); } catch {}
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={hidden}
      title="Translator's notes"
      className="inline-flex h-9 items-center whitespace-nowrap rounded-sm px-2.5 text-ink-soft transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-ink aria-pressed:bg-accent-soft aria-pressed:text-accent"
    >
      {/* Phones: one word; the pressed state shows whether notes are hidden. */}
      <span className="sm:hidden" aria-hidden>Notes</span>
      <span className="sr-only sm:not-sr-only">{hidden ? "Show notes" : "Hide notes"}</span>
    </button>
  );
}

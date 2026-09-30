"use client";

import BOOK from "@/book.json";
import { useEffect, useState } from "react";

const KEY = "german-all";

/** Opens every German panel on the page at once (sets data-german on <html>). */
export function ShowAllGerman() {
  const [on, setOn] = useState(false);

  // Remembered for this tab, so German stays on while browsing (search results open new pages).
  useEffect(() => {
    let saved = false;
    try { saved = sessionStorage.getItem(KEY) === "1"; } catch {}
    if (saved) {
      setOn(true);
      document.documentElement.setAttribute("data-german-all", "");
    }
  }, []);

  function toggle() {
    const next = !on;
    setOn(next);
    document.documentElement.toggleAttribute("data-german-all", next);
    try { sessionStorage.setItem(KEY, next ? "1" : "0"); } catch {}
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={on}
      className="inline-flex h-9 items-center whitespace-nowrap rounded-sm px-2.5 text-ink-soft transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-ink aria-pressed:bg-accent-soft aria-pressed:text-accent"
    >
      <span className="sm:hidden" aria-hidden>{BOOK.source.name}</span>
      <span className="sr-only sm:not-sr-only">{on ? `Hide ${BOOK.source.name}` : `Show ${BOOK.source.name}`}</span>
    </button>
  );
}

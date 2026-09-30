"use client";

import { useEffect, useState } from "react";

const KEY = "toc-collapsed";

/** The collapsed chapter groups live on <html data-toc-collapsed="g-7 g-8 …"> (set before first paint by the
 * layout), so CSS hides them without a flash; these controls edit that list and remember it. */
function read(): string[] {
  return (document.documentElement.getAttribute("data-toc-collapsed") ?? "").split(" ").filter(Boolean);
}

function write(ids: string[]) {
  document.documentElement.setAttribute("data-toc-collapsed", ids.join(" "));
  try { localStorage.setItem(KEY, ids.join(" ")); } catch {}
  window.dispatchEvent(new Event("toc-collapsed"));
}

function useCollapsed(): string[] {
  const [ids, setIds] = useState<string[]>([]);
  useEffect(() => {
    const sync = () => setIds(read());
    sync();
    window.addEventListener("toc-collapsed", sync);
    return () => window.removeEventListener("toc-collapsed", sync);
  }, []);
  return ids;
}

/** Chevron beside a chapter in the contents: shows or hides its sections. */
export function TocToggle({ group, title }: { group: string; title: string }) {
  const collapsed = useCollapsed().includes(group);
  return (
    <button
      type="button"
      aria-expanded={!collapsed}
      aria-controls={`${group}-sections`}
      aria-label={`${collapsed ? "Show" : "Hide"} sections of ${title}`}
      onClick={() => {
        const ids = read();
        write(ids.includes(group) ? ids.filter((i) => i !== group) : [...ids, group]);
      }}
      className="toc-chevron -ml-1.5 flex size-7 shrink-0 items-center justify-center rounded-sm text-ink-faint transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
    >
      <svg viewBox="0 0 12 12" className="size-3" aria-hidden>
        <path d="M3 4.5 6 7.5 9 4.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </button>
  );
}

/** "Collapse all" / "Expand all" beside the Contents heading. */
export function TocToggleAll({ groups }: { groups: string[] }) {
  const ids = useCollapsed();
  const allCollapsed = groups.every((g) => ids.includes(g));
  return (
    <button
      type="button"
      onClick={() => write(allCollapsed ? [] : groups)}
      className="rounded-sm px-1.5 py-1 font-sans text-meta text-ink-faint transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
    >
      {allCollapsed ? "Expand all" : "Collapse all"}
    </button>
  );
}

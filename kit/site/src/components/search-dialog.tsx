"use client";

import BOOK from "@/book.json";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PageUnit } from "@/lib/content";

type Result = { url: string; excerpt: string; title: string };

type PagefindData = {
  url: string;
  excerpt: string;
  meta: { title?: string };
  sub_results?: { url: string; excerpt: string; title: string }[];
};

type Pagefind = {
  debouncedSearch: (q: string) => Promise<{ results: { data: () => Promise<PagefindData> }[] } | null>;
};

type Lang = "en" | "de";
const pagefindPromises: Partial<Record<Lang, Promise<Pagefind | null>>> = {};

/** English by default; the German index only while the German text is shown ("Show German"). */
function searchLang(): Lang {
  return document.documentElement.hasAttribute("data-german-all") ? "de" : "en";
}

/** Pagefind's indexes are generated after `next build`, so they're loaded at runtime. */
function loadPagefind(lang: Lang): Promise<Pagefind | null> {
  const bundle = lang === "de" ? "/pagefind-de/pagefind.js" : "/pagefind/pagefind.js";
  pagefindPromises[lang] ??= import(/* webpackIgnore: true */ /* turbopackIgnore: true */ bundle)
    .then((m) => m as Pagefind)
    .catch(() => null);
  return pagefindPromises[lang];
}

/** "480", "p. 480", "page 480", "S. 480", "Seite 480" → 480. */
function pageQuery(q: string): number | null {
  const m = q.trim().match(/^(?:pp?\.?|pages?|s\.?|seite)?\s*(\d{1,4})$/i);
  return m ? Number(m[1]) : null;
}

/** The unit holding printed page n, and the anchor to jump to: that page, or the nearest earlier one with an
 * anchor (a page that is all figure has none of its own). */
function findPage(index: PageUnit[], n: number): { url: string; title: string } | null {
  const unit = index.find((u) => u.first <= n && n <= u.last);
  if (!unit) return null;
  const at = [...unit.pages].reverse().find((p) => p <= n);
  return { url: `/chapter/${unit.slug}${at !== undefined ? `#page-${at}` : ""}`, title: unit.title };
}

export function SearchDialog({ pageIndex }: { pageIndex: PageUnit[] }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [status, setStatus] = useState<"idle" | "searching" | "unavailable">("idle");
  const [lang, setLang] = useState<Lang>("en");
  const pageNumber = pageQuery(query);
  const pageHit = useMemo(() => (pageNumber === null ? null : findPage(pageIndex, pageNumber)), [pageIndex, pageNumber]);

  const open = useCallback(() => {
    const current = searchLang();
    setLang(current);
    dialogRef.current?.showModal();
    void loadPagefind(current);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const typing = e.target instanceof HTMLElement && ["INPUT", "TEXTAREA"].includes(e.target.tagName);
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !typing)) {
        e.preventDefault();
        open();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setStatus("searching");
    loadPagefind(lang).then(async (pf) => {
      if (!pf) return !cancelled && setStatus("unavailable");
      const search = await pf.debouncedSearch(query);
      if (!search || cancelled) return;
      const data = await Promise.all(search.results.slice(0, 12).map((r) => r.data()));
      if (cancelled) return;
      // Prefer section-level hits (headings carry ids), so a result jumps to the passage.
      setResults(
        data.flatMap((d) =>
          d.sub_results?.length
            ? d.sub_results.slice(0, 3).map((s) => ({ url: s.url, excerpt: s.excerpt, title: s.title }))
            : [{ url: d.url, excerpt: d.excerpt, title: d.meta.title ?? d.url }],
        ),
      );
      setStatus("idle");
    });
    return () => {
      cancelled = true;
    };
  }, [query, lang]);

  return (
    <>
      <button
        type="button"
        onClick={open}
        className="inline-flex h-9 items-center gap-2 whitespace-nowrap rounded-sm px-2.5 text-ink-soft transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-ink"
      >
        Search
        <kbd className="hidden rounded-[3px] border border-rule px-1 font-sans text-[0.7rem] text-ink-faint sm:inline">⌘K</kbd>
      </button>

      <dialog
        ref={dialogRef}
        onClose={() => setQuery("")}
        onClick={(e) => e.target === dialogRef.current && dialogRef.current?.close()}
        className="mx-auto mt-[12vh] w-[min(40rem,calc(100vw-2rem))] rounded-md border border-rule bg-paper p-0 text-ink shadow-2xl backdrop:bg-ink/25 backdrop:backdrop-blur-[2px]"
        aria-label="Search the book"
      >
        <div className="border-b border-rule p-3">
          <input
            autoFocus
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              // A page number: Enter goes straight to the page.
              if (e.key === "Enter" && pageHit) {
                dialogRef.current?.close();
                window.location.assign(pageHit.url);
              }
            }}
            placeholder={lang === "de" ? `Search the ${BOOK.source.name} text — ${BOOK.searchExamples.source}` : `Search the book — ${BOOK.searchExamples.en}`}
            className="w-full bg-transparent px-2 py-2 font-sans text-body outline-none placeholder:text-ink-faint"
            aria-label={lang === "de" ? `Search the ${BOOK.source.name} text` : "Search"}
          />
        </div>
        <div className="max-h-[60vh] overflow-y-auto p-2 font-sans" aria-live="polite">
          {status === "unavailable" && (
            <p className="p-3 text-note text-ink-faint">Search index not built — run <code>npm run build</code>.</p>
          )}
          {pageNumber !== null && (
            pageHit ? (
              <a
                href={pageHit.url}
                onClick={() => dialogRef.current?.close()}
                className="mb-1 flex items-baseline justify-between gap-3 rounded-sm border border-rule px-3 py-2.5 transition-colors duration-150 ease-out-soft hover:border-accent hover:bg-tint focus-visible:bg-tint"
              >
                <span className="text-note font-semibold text-ink">
                  Go to page <span className="tabular-nums">{pageNumber}</span>
                </span>
                <span className="truncate text-meta text-ink-faint">{pageHit.title} · ↵</span>
              </a>
            ) : (
              <p className="p-3 text-note text-ink-faint">
                Page <span className="tabular-nums">{pageNumber}</span> isn&apos;t in this edition.
              </p>
            )
          )}
          {query && status === "idle" && results.length === 0 && pageNumber === null && (
            <p className="p-3 text-note text-ink-faint">No matches.</p>
          )}
          <ul>
            {results.map((r) => (
              <li key={r.url + r.excerpt.slice(0, 20)}>
                <a
                  href={r.url}
                  onClick={() => dialogRef.current?.close()}
                  className="block rounded-sm px-3 py-2.5 transition-colors duration-150 ease-out-soft hover:bg-tint focus-visible:bg-tint"
                >
                  <span className="block text-note font-semibold text-ink">{r.title}</span>
                  <span
                    className="mt-0.5 block text-note text-ink-soft [&_mark]:bg-accent-soft [&_mark]:text-accent"
                    dangerouslySetInnerHTML={{ __html: r.excerpt }}
                  />
                </a>
              </li>
            ))}
          </ul>
        </div>
      </dialog>
    </>
  );
}

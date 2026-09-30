import type { ReactNode } from "react";
import type { SideNote } from "@/lib/content";
import { GermanToggle } from "@/components/german-toggle";
import BOOK from "@/book.json";
import { SideNotes } from "@/components/side-notes";

/**
 * One row of the chapter grid:
 *   gutter (page number when it changes, DE toggle) · reading column · margin notes.
 * Below xl the margin collapses and notes sit under the text (tap to expand).
 */
export function BlockRow({
  id,
  page,
  showPage,
  german,
  notes,
  searchEn = true,
  wide = false,
  children,
}: {
  id: string;
  page: number | string | null;
  showPage: boolean;
  german?: ReactNode;
  notes: SideNote[];
  /** Headings stay in both search indexes so German hits still jump to their section. */
  searchEn?: boolean;
  /** A dense figure (callout layouts) takes the margin column too, when the row has no notes of its own. */
  wide?: boolean;
  children: ReactNode;
}) {
  const panelId = `${id}-de`;
  const spread = wide && notes.length === 0;
  return (
    <div className="group/row relative grid grid-cols-[minmax(0,1fr)] md:grid-cols-[3.5rem_minmax(0,42rem)] md:gap-x-6 xl:grid-cols-[3.5rem_minmax(0,42rem)_17rem] xl:gap-x-10">
      {/* Jump target for "Go to page N" in search: the first block of each printed page. */}
      {showPage && page !== null && <span id={`page-${page}`} className="absolute top-0 scroll-mt-24" aria-hidden />}
      <div className="hidden md:flex md:flex-col md:items-end md:gap-1 md:pt-1" data-pagefind-ignore="all">
        {showPage && page !== null && (
          <span className="font-sans text-meta tabular-nums text-ink-faint" aria-label={`Page ${page}`}>
            {page}
          </span>
        )}
        {german && <GermanToggle panelId={panelId} page={page} />}
      </div>

      <div className={`reading min-w-0 ${spread ? "xl:col-span-2" : ""}`}>
        {searchEn ? <div data-search="en">{children}</div> : children}
        {german && (
          <div id={panelId} className="de-panel" lang={BOOK.source.code} data-pagefind-ignore="all" data-search="de">
            <div className="overflow-hidden">
              <div className="mt-3 border-l-2 border-accent/40 bg-tint py-3 pl-4 pr-3 text-ink-soft">{german}</div>
            </div>
          </div>
        )}
        {german && (
          <div className="mt-1 flex justify-end md:hidden" data-pagefind-ignore="all">
            <GermanToggle panelId={panelId} page={page} />
          </div>
        )}
        <SideNotes notes={notes} variant="inline" />
      </div>

      {!spread && <SideNotes notes={notes} variant="margin" />}
    </div>
  );
}

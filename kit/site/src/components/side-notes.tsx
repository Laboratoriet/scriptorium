import type { SideNote } from "@/lib/content";

/**
 * Translator's notes. Two renderings of the same notes, one shown per breakpoint:
 * - margin: Tufte-style sidenotes in the right column (xl and up)
 * - inline: collapsed <details> under the text (below xl), tap to expand
 */
export function SideNotes({ notes, variant }: { notes: SideNote[]; variant: "margin" | "inline" }) {
  if (notes.length === 0) return variant === "margin" ? <div className="hidden xl:block" /> : null;

  if (variant === "margin") {
    return (
      <aside className="hidden xl:block xl:h-0 xl:overflow-visible" aria-label="Translator's notes" data-search="en" data-sidenotes>
        <ol className="space-y-3 pt-1 font-sans text-note text-ink-soft">
          {notes.map((note) => (
            <li key={note.n} id={`tn-${note.n}`} className="prose-book">
              <span className="mr-1 font-semibold text-remark">{note.n}</span>
              <span dangerouslySetInnerHTML={{ __html: note.html }} />
            </li>
          ))}
        </ol>
      </aside>
    );
  }

  return (
    <div className="tn-inline mt-2 space-y-1 xl:hidden" data-search="en">
      {notes.map((note) => (
        <details key={note.n} className="group rounded-sm font-sans text-note text-ink-soft">
          <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 text-note marker:hidden hover:text-ink">
            <span className="font-semibold text-remark">{note.n}</span>
            <span>Translator&rsquo;s note</span>
            <span aria-hidden className="text-ink-faint transition-transform duration-200 ease-out-soft group-open:rotate-90">
              ›
            </span>
          </summary>
          <p className="prose-book border-l-2 border-remark/40 pb-2 pl-3" dangerouslySetInnerHTML={{ __html: note.html }} />
        </details>
      ))}
    </div>
  );
}

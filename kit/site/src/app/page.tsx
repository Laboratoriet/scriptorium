import Link from "next/link";
import BOOK from "@/book.json";
import { getAvailableChapters, getChapter, getToc, type TocEntry } from "@/lib/content";
import { TocToggle, TocToggleAll } from "@/components/toc-toggle";

/** English section titles for translated chapters, keyed by section number. */
async function englishTitles(): Promise<Map<string, string>> {
  const titles = new Map<string, string>();
  for (const n of await getAvailableChapters()) {
    for (const b of (await getChapter(n)).blocks) {
      if (b.type === "heading" && b.anchor) titles.set(b.anchor.slice(2), b.en.replace(/<sup[^>]*>.*?<\/sup>/g, "").replace(/<[^>]+>/g, "").trim());
    }
  }
  return titles;
}

function Entry({ entry, en, toggle }: { entry: TocEntry; en?: string; toggle?: React.ReactNode }) {
  const isChapter = entry.kind === "chapter" && /^\d+$/.test(entry.id);
  const depth = entry.kind === "section" ? entry.id.split(".").length - 1 : 0;
  const href = isChapter ? `/chapter/${entry.unit}/` : `/chapter/${entry.unit}/#s-${entry.id}`;
  // Headings from translated text win; otherwise the translated contents title.
  const title = en ?? entry.en ?? entry.de;

  const label = (
    <>
      <span className="min-w-0">
        {(isChapter || (entry.kind === "section" && /^\d+(\.\d+)*$/.test(entry.id))) && (
          <span className="mr-2 font-sans tabular-nums text-ink-faint">{entry.id}</span>
        )}
        <span className={entry.kind === "excursus" ? "italic" : ""}>{title}</span>
        {isChapter && !entry.available && (
          <span className="ml-2 font-sans text-meta font-normal text-ink-faint">not yet translated</span>
        )}
      </span>
      <span className="font-sans text-meta tabular-nums text-ink-faint">{entry.page}</span>
    </>
  );

  const row = `flex items-baseline justify-between gap-4 py-1.5 ${isChapter ? "mt-5 font-semibold text-ink" : "text-ink-soft"}`;
  const link = entry.available ? (
    <Link href={href} className={`${row} min-w-0 flex-1 rounded-sm transition-colors duration-150 ease-out-soft hover:text-accent`}>
      {label}
    </Link>
  ) : (
    <div className={`${row} min-w-0 flex-1 opacity-70`}>{label}</div>
  );
  return (
    <div style={{ paddingLeft: `${Math.max(0, depth - 1) * 1.25}rem` }} lang={en || entry.en ? "en" : "de"} className="flex items-baseline gap-1">
      {/* Chapter rows keep a slot for the chevron, so titles line up whether or not they have sections. */}
      {depth === 0 && <span className={`flex w-6 shrink-0 self-center ${isChapter ? "mt-5" : ""}`}>{toggle}</span>}
      {link}
    </div>
  );
}

export default async function Home() {
  const [toc, titles] = await Promise.all([getToc(), englishTitles()]);
  // Sections are only listed for chapters that are translated; the rest stays compact.
  const visible = toc.filter((e) => e.kind !== "section" || e.available);
  // Each top-level entry with the sections that follow it: one collapsible group.
  const groups: { head: TocEntry; sections: TocEntry[] }[] = [];
  for (const e of visible) {
    if (e.kind === "section" && groups.length) groups[groups.length - 1].sections.push(e);
    else groups.push({ head: e, sections: [] });
  }
  const gid = (e: TocEntry) => `g-${e.id.replace(/[^\w-]/g, "_")}`;
  const collapsible = groups.filter((g) => g.sections.length).map((g) => gid(g.head));
  // Collapsed groups are listed on <html data-toc-collapsed> (set before first paint): one rule per group.
  const css = collapsible
    .map((g) => `:root[data-toc-collapsed~="${g}"] [data-group="${g}"]`)
    .join(",");

  return (
    <main className="mx-auto max-w-[42rem] px-4 pb-24 pt-14 md:pt-20">
      <header className="mb-14">
        <p className="font-sans text-meta uppercase tracking-[0.14em] text-ink-faint">
          {BOOK.authors.join(" · ")}
        </p>
        <h1 className="mt-4 font-serif text-h1 font-semibold tracking-tight text-balance">{BOOK.title}</h1>
        <p className="mt-2 font-serif text-h3 italic text-ink-soft">{BOOK.subtitle}</p>
        <p className="mt-6 font-sans text-note text-ink-soft text-pretty" dangerouslySetInnerHTML={{ __html: BOOK.intro }} />
      </header>

      <nav aria-label="Contents">
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="font-sans text-meta font-semibold uppercase tracking-wider text-ink-faint">Contents</h2>
          <TocToggleAll groups={collapsible} />
        </div>
        {css && <style>{`${css} { --toc-rows: 0fr; --toc-vis: hidden; --toc-turn: -90deg; }`}</style>}
        <ol className="border-t border-rule">
          {groups.map(({ head, sections }) => (
            <li key={head.id} data-group={gid(head)}>
              <Entry
                entry={head}
                en={titles.get(head.id)}
                toggle={sections.length ? <TocToggle group={gid(head)} title={titles.get(head.id) ?? head.en ?? head.de} /> : null}
              />
              {sections.length > 0 && (
                <div id={`${gid(head)}-sections`} className="toc-sections">
                  <ol className="min-h-0 overflow-hidden pl-7">
                    {sections.map((entry) => (
                      <li key={entry.id}>
                        <Entry entry={entry} en={titles.get(entry.id)} />
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </main>
  );
}

import type { Block, Chapter, FootnoteBlock } from "@/lib/content";
import { BlockRow } from "@/components/block-row";
import { FigureView } from "@/components/figure-block";
import { OriginalToggle } from "@/components/original-toggle";

const html = (s: string) => ({ __html: s });

function Heading({ block, id }: { block: Extract<Block, { type: "heading" }>; id: string }) {
  const Tag = block.level === 1 ? "h1" : block.level === 2 ? "h2" : "h3";
  const size = block.level === 1 ? "text-h1 mt-2 mb-2" : block.level === 2 ? "text-h2 mt-14 mb-5" : "text-h3 mt-10 mb-4";
  return (
    <Tag id={id} className={`scroll-mt-24 font-serif font-semibold tracking-tight text-ink text-balance hyphens-auto [overflow-wrap:anywhere] ${size}`}>
      {block.number && (
        <span className="mr-3 font-sans font-semibold tabular-nums text-ink-faint">{block.number}</span>
      )}
      {block.number && " "}
      <span dangerouslySetInnerHTML={html(block.en)} />
    </Tag>
  );
}

function References({ block }: { block: Extract<Block, { type: "references" }> }) {
  return (
    <ol className="prose-book space-y-1.5 font-sans text-note text-ink-soft">
      {block.refs.map((r) => (
        <li key={r.n} id={`ref-${block.scope}-${r.n}`} className="grid scroll-mt-24 grid-cols-[2.25rem_minmax(0,1fr)] target:bg-accent-soft">
          <span className="tabular-nums text-ink-faint">[{r.n}]</span>
          <span className="[overflow-wrap:anywhere]">
            <span dangerouslySetInnerHTML={html(r.html)} />
            {r.href && (
              <a
                href={r.href}
                target="_blank"
                rel="noreferrer"
                aria-label={`${r.link === "doi" ? "DOI" : "Link"} for reference ${r.n} (opens in a new tab)`}
                className="ml-1.5 whitespace-nowrap text-meta text-ink-faint underline decoration-rule underline-offset-2 transition-colors duration-150 ease-out-soft hover:text-accent hover:decoration-accent"
              >
                {r.link === "doi" ? "DOI" : "Link"} ↗
              </a>
            )}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Footnotes({ notes }: { notes: FootnoteBlock[] }) {
  if (notes.length === 0) return null;
  return (
    <section aria-label="Footnotes" className="mt-12 border-t border-rule pt-6" data-search="en">
      <h2 className="mb-3 font-sans text-meta font-semibold uppercase tracking-wider text-ink-faint">Footnotes</h2>
      <ol className="prose-book space-y-2 font-sans text-note text-ink-soft">
        {notes.map((f) => (
          <li key={f.id} id={`fn-${f.id}`} className="scroll-mt-24">
            <a href={`#fnref-${f.id}`} className="mr-2 text-note no-underline" aria-label="Back to text">
              *
            </a>
            <span dangerouslySetInnerHTML={html(f.en)} />
          </li>
        ))}
      </ol>
    </section>
  );
}

export async function ChapterBody({ chapter }: { chapter: Chapter }) {
  let lastPage: number | string | null = null;
  const footnotes = chapter.blocks.filter((b): b is FootnoteBlock => b.type === "footnote");
  const rows = [];

  for (const [i, block] of chapter.blocks.entries()) {
    if (block.type === "footnote") continue;
    const id = `b${i}`;
    const showPage = block.page !== lastPage;
    lastPage = block.page;

    let body: React.ReactNode;
    let german: React.ReactNode | undefined;

    switch (block.type) {
      case "heading":
        body = <Heading block={block} id={block.anchor ?? id} />;
        break;
      case "paragraph":
        // Lists (and the odd rule) come through as paragraphs; they can't sit inside a <p>.
        if (/^<(ul|ol|hr|blockquote|table|h[1-6]|div|p)\b/.test(block.en)) {
          body = <div className="prose-book prose-lists mb-5 text-pretty hyphens-auto" dangerouslySetInnerHTML={html(block.en)} />;
          german = <div className="prose-book prose-lists text-pretty hyphens-auto" dangerouslySetInnerHTML={html(block.de)} />;
        } else {
          body = <p className="prose-book mb-5 text-pretty hyphens-auto" dangerouslySetInnerHTML={html(block.en)} />;
          german = <p className="prose-book text-pretty hyphens-auto" dangerouslySetInnerHTML={html(block.de)} />;
        }
        break;
      case "table":
        body = (
          <figure className="my-8">
            {block.caption_en && (
              <figcaption className="prose-book mb-3 font-sans text-note text-ink-soft" dangerouslySetInnerHTML={html(block.caption_en)} />
            )}
            <div className="prose-book overflow-x-auto" tabIndex={0} dangerouslySetInnerHTML={html(block.en)} />
            {block.original && (
              <OriginalToggle
                src={block.original.src}
                width={block.original.width}
                height={block.original.height}
                alt="Printed original of this table"
              />
            )}
          </figure>
        );
        german = (
          <div className="prose-book overflow-x-auto">
            {block.caption_de && <p className="mb-2 text-note" dangerouslySetInnerHTML={html(block.caption_de)} />}
            <div dangerouslySetInnerHTML={html(block.de)} />
          </div>
        );
        break;
      case "figure":
        body = <FigureView block={block} />;
        german = block.caption_de ? <p className="prose-book text-note" dangerouslySetInnerHTML={html(block.caption_de)} /> : undefined;
        break;
      case "references":
        body = <References block={block} />;
        break;
    }

    rows.push(
      <BlockRow
        key={id}
        id={id}
        page={block.page}
        showPage={showPage}
        german={german}
        notes={block.tns}
        searchEn={block.type !== "heading"}
        wide={block.type === "figure" && Boolean(block.scheme?.wide)}
      >
        {body}
      </BlockRow>,
    );
  }

  return (
    <>
      {rows}
      <BlockRow id="footnotes" page={null} showPage={false} notes={footnotes.flatMap((f) => f.tns)}>
        <Footnotes notes={footnotes} />
      </BlockRow>
    </>
  );
}

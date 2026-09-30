import type { FigureBlock } from "@/lib/content";
import { getSvg } from "@/lib/content";
import { BarChart } from "@/components/bar-chart";
import { LineChart } from "@/components/line-chart";
import { SchemeView } from "@/components/scheme-view";
import { OriginalToggle } from "@/components/original-toggle";

function FigureCaption({ label, html }: { label: string; html: string }) {
  const english = label.replace(/^Abb\./, "Fig.");
  return (
    <figcaption className="prose-book mt-3 font-sans text-note text-ink-soft">
      {english && <span className="mr-1.5 font-semibold text-ink">{english}</span>}
      <span dangerouslySetInnerHTML={{ __html: html }} />
    </figcaption>
  );
}

/** Molecules redrawn from verified SMILES, one card per compound number. */
async function Structures({ block }: { block: FigureBlock }) {
  const all = block.compounds ?? [];
  const svgs = new Map(await Promise.all(all.map(async (c) => [c.key, await getSvg(c.svg)] as const)));
  if (block.groups) {
    // A table printed as an image: one column of cards per printed column, stacked on small screens.
    return (
      <div className="grid gap-x-8 gap-y-10 md:grid-cols-3">
        {block.groups.map((g) => (
          <section key={g.en} aria-label={g.en}>
            <h4 className="mb-4 border-b border-rule pb-1.5 text-center font-sans text-note font-semibold text-ink">{g.en}</h4>
            <CardRow compounds={all.filter((c) => g.compounds.includes(c.number))} svgs={svgs} />
          </section>
        ))}
      </div>
    );
  }
  return <CardRow compounds={all} svgs={svgs} />;
}

function CardRow({ compounds, svgs }: { compounds: NonNullable<FigureBlock["compounds"]>; svgs: Map<string, string> }) {
  return (
    // Cards take the width of their molecule, so every structure keeps the same bond length (book scale).
    <div className="flex flex-wrap items-end justify-center gap-x-10 gap-y-10">
      {compounds.map((c) => (
        <div key={c.key} id={`cpd-${c.key}`} className="flex min-w-[7rem] max-w-full scroll-mt-24 flex-col items-center text-center">
          <div
            className="structure max-w-full"
            role="img"
            aria-label={c.number ? `Structure of compound ${c.number}` : `Structure of ${c.names_en[0]?.replace(/<[^>]+>/g, "") ?? "the compound"}`}
            dangerouslySetInnerHTML={{ __html: svgs.get(c.key) ?? "" }}
          />
          {c.number && <p className="mt-1 font-sans text-note font-bold text-ink tabular-nums">{c.number}</p>}
          <ul className="prose-book mt-1 max-w-[16rem] space-y-0.5 font-sans text-meta text-ink-soft text-balance">
            {c.names_en.map((name) => (
              <li
                key={name}
                title={c.name_source === "pubchem" ? "Name from PubChem (not printed in the book)" : undefined}
                dangerouslySetInnerHTML={{ __html: name }}
              />
            ))}
          </ul>
          {c.status === "read-twice" ? (
            // Weaker evidence than a name match, so it is said on the card, not hidden. When PubChem knows the
            // structure, its entry is linked too (the structure exists; no printed name was checked against it).
            <p className="mt-1.5 font-sans text-meta text-ink-faint">
              <span title="The book prints no name to check against. Two independent readings of the printed structure agree.">
                Read from drawing
              </span>
              {c.cid && (
                <>
                  {" · "}
                  <a
                    href={`https://pubchem.ncbi.nlm.nih.gov/compound/${c.cid}`}
                    className="underline decoration-rule underline-offset-2 transition-colors duration-150 ease-out-soft hover:text-accent hover:decoration-accent"
                    rel="noreferrer"
                    target="_blank"
                  >
                    PubChem {c.cid}
                  </a>
                </>
              )}
            </p>
          ) : (
            <a
              href={`https://pubchem.ncbi.nlm.nih.gov/compound/${c.cid}`}
              className="mt-1.5 font-sans text-meta text-ink-faint underline decoration-rule underline-offset-2 transition-colors duration-150 ease-out-soft hover:text-accent hover:decoration-accent"
              rel="noreferrer"
              target="_blank"
            >
              PubChem {c.cid}
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

/** English key to the text printed inside a figure that is shown as the original. */
function LabelKey({ labels }: { labels: string[] }) {
  const words = labels.filter((l) => /[a-z]{3,}/i.test(l.replace(/<[^>]+>/g, "")));
  if (words.length === 0) return null;
  return (
    <details className="label-key mt-2 font-sans text-meta text-ink-soft">
      <summary className="inline-flex min-h-9 cursor-pointer list-none items-center gap-1.5 text-ink-faint hover:text-accent [&::-webkit-details-marker]:hidden">
        <span aria-hidden>›</span> English labels
      </summary>
      <ul className="prose-book mt-1 columns-2 gap-6 sm:columns-3">
        {words.map((l) => (
          <li key={l} className="break-inside-avoid py-0.5" dangerouslySetInnerHTML={{ __html: l }} />
        ))}
      </ul>
    </details>
  );
}

export async function FigureView({ block }: { block: FigureBlock }) {
  const asStructures = block.kind === "structure" || block.kind === "table-image";
  const redrawn =
    (asStructures && !!block.compounds?.length) ||
    (block.kind === "chart" && !!block.chart) ||
    !!block.scheme ||
    !!block.document_en ||
    !!block.merged_into ||
    !!block.illustration;
  // Real compounds redrawn, generic ones (R, X …) only in the print: the original stays in view.
  const partial = redrawn && !!block.partial;

  return (
    <figure id={block.id} className="my-8 scroll-mt-24">
      {block.merged_into && (
        <p className="rounded-sm border border-rule bg-tint px-4 py-3 text-center font-sans text-note text-ink-soft">
          This page continues{" "}
          <a href={`#${block.merged_into.id}`} className="font-semibold text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent">
            {block.merged_into.label}
          </a>{" "}
          — both printed pages are redrawn there as one figure.
        </p>
      )}
      {block.document_en && (
        <>
          <div
            className="prose-book doc-text mx-auto max-w-xl rounded-sm border border-rule bg-tint px-5 py-4 font-serif text-note leading-relaxed text-ink [&_p+p]:mt-2.5"
            dangerouslySetInnerHTML={{ __html: block.document_en }}
          />
          <p className="provenance mt-2 text-center font-sans text-meta text-ink-faint">English translation of the printed document — the original German below.</p>
        </>
      )}
      {block.illustration && (
        <>
          {/* Scrolls sideways on phones rather than shrinking its labels below reading size. */}
          <div className="overflow-x-auto" tabIndex={0} aria-label="Diagram (scrolls sideways on small screens)">
            <div
              className="mx-auto min-w-[34rem] max-w-2xl text-ink [&_svg]:h-auto [&_svg]:w-full"
              dangerouslySetInnerHTML={{ __html: await getSvg(block.illustration, 1) }}
            />
          </div>
          <p className="provenance mt-3 text-center font-sans text-meta text-ink-faint">Redrawn from the printed diagram — compare with the original below.</p>
        </>
      )}
      {block.scheme && <SchemeView scheme={block.scheme} />}
      {block.scheme?.generic && (
        <p className="provenance mt-3 text-center font-sans text-meta text-ink-faint">
          Generic structures (R groups, variable positions) redrawn from the print — compare with the original below.
        </p>
      )}
      {block.scheme?.classmap && (
        <p className="provenance mt-3 text-center font-sans text-meta text-ink-faint">
          Redrawn from the print{block.scheme.checked ? " (two independent readings agree)" : ""}
          {Object.values(block.scheme.nodes).some((n) => n.chapter_href) ? " — each class links to its section" : ""}; compare with the
          original below.
        </p>
      )}
      {block.scheme?.checked && !block.scheme.classmap && (
        <p className="provenance mt-3 text-center font-sans text-meta text-ink-faint">
          Redrawn from the printed scheme (two independent readings agree) — compare with the original below.
        </p>
      )}
      {block.scheme?.pilot && (
        <p className="provenance mt-3 text-center font-sans text-meta text-ink-faint">
          Redrawn from the printed scheme (pilot, one reading) — compare with the original below.
        </p>
      )}
      {asStructures && redrawn && !block.scheme && <Structures block={block} />}
      {block.kind === "chart" && block.chart && !block.scheme && (block.chart.type === "line" ? <LineChart chart={block.chart} /> : <BarChart chart={block.chart} />)}
      {partial && block.original && (
        <div className="mt-8">
          {/* The cleaned page when there is one (contrast/sharpening only), else the scan. */}
          {/* eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP */}
          <img
            src={(block.restored ?? block.original).src}
            width={(block.restored ?? block.original).width}
            height={(block.restored ?? block.original).height}
            alt={`${block.label || "Figure"} (printed original, with the generic structures)`}
            loading="lazy"
            className="scan mx-auto h-auto w-full max-w-xl rounded-sm"
          />
          <p className="provenance mt-2 text-center font-sans text-meta text-ink-faint">Printed original — generic structures (R, X …)</p>
        </div>
      )}
      {!redrawn && !partial && block.restored && (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP */}
          <img
            src={block.restored.src}
            width={block.restored.width}
            height={block.restored.height}
            alt={`${block.label || "Figure"} (restored from the printed page)`}
            loading="lazy"
            className="scan mx-auto h-auto w-full max-w-xl rounded-sm"
          />
          <p className="provenance mt-2 text-center font-sans text-meta text-ink-faint">
            {block.restored.method === "cleanup"
              ? "Cleaned from the printed page (contrast and sharpening only, nothing redrawn) — the scan is below."
              : "Restored from the printed page (cleaned and upscaled) — small print may differ from the book; compare below."}
          </p>
        </>
      )}
      {!redrawn && !block.restored && block.original && (
        // eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP
        <img
          src={block.original.src}
          width={block.original.width}
          height={block.original.height}
          alt={`${block.label || "Figure"} (printed original)`}
          loading="lazy"
          className="scan mx-auto h-auto w-full max-w-xl rounded-sm"
        />
      )}
      {block.pending && !block.restored && (
        <p className="provenance mt-2 text-center font-sans text-meta text-ink-faint">
          Printed original
        </p>
      )}
      {(block.label || !redrawn) && <FigureCaption label={block.label} html={block.caption_en} />}
      {(!redrawn || partial) && block.labels_en && <LabelKey labels={block.labels_en} />}
      {((redrawn && !partial) || block.restored) && block.original && (
        <OriginalToggle
          src={block.original.src}
          width={block.original.width}
          height={block.original.height}
          alt={`Printed original of ${block.label || "this figure"}`}
          id={block.id}
        />
      )}
    </figure>
  );
}

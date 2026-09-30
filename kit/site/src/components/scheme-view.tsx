import type { SchemeData, SchemeNode } from "@/lib/content";
import { getSvg } from "@/lib/content";
import { ClassMapArrows } from "@/components/class-map-arrows";

const html = (s: string) => ({ __html: s });

/** Schemes put several molecules side by side, so they stay at the book's own scale; generic structure
 * figures (no arrows) use the cards' 1.4× like every other structure. */
const SCHEME_SCALE = 1;

/** Arrow directions as angles (degrees, 0 = right, clockwise, as in SVG). */
const ANGLE: Record<string, number> = {
  right: 0, "down-right": 45, down: 90, "down-left": 135, left: 180, "up-left": 225, up: 270, "up-right": 315,
};

function Arrow({ direction, style = "line", heads, long = false }: { direction: string; style?: "line" | "open" | "blocked"; heads?: "both"; long?: boolean }) {
  const both = direction === "both";
  const angle = both ? 0 : ANGLE[direction] ?? 0;
  const vertical = angle === 90 || angle === 270;
  const diagonal = angle % 90 !== 0;
  // One arrow shape (pointing right), turned by the direction; the box matches its orientation.
  // A long vertical arrow (an axis over several rows) stretches to the height of its cell.
  const box = vertical
    ? { vb: "-14 -40 28 80", cls: long ? "h-full min-h-16 w-7" : "h-16 w-7" }
    : diagonal
      ? { vb: "-30 -30 60 60", cls: "size-14" }
      : { vb: "-40 -14 80 28", cls: "h-7 w-20" };
  const len = diagonal ? 24 : 32;
  return (
    <svg viewBox={box.vb} className={box.cls} preserveAspectRatio={long ? "none" : undefined} aria-hidden>
      <g transform={`rotate(${angle})`} stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke">
        {both ? (
          // Equilibrium: two half-headed arrows.
          <>
            <line x1={-len} y1="-4" x2={len} y2="-4" />
            <polyline points={`${len - 8},-11 ${len},-4`} />
            <line x1={len} y1="4" x2={-len} y2="4" />
            <polyline points={`${-len + 8},11 ${-len},4`} />
            {style === "blocked" && <path d="M -7 -11 L 7 11 M -7 11 L 7 -11" />}
          </>
        ) : style === "open" ? (
          // The book's hollow block arrow: a structural change, not a reaction.
          heads === "both" ? (
            // Double-headed block arrow: a relation both ways (e.g. "contains the substructure").
            <polygon points={`${-len},0 ${-len + 10},-10 ${-len + 10},-4 ${len - 10},-4 ${len - 10},-10 ${len},0 ${len - 10},10 ${len - 10},4 ${-len + 10},4 ${-len + 10},10`} />
          ) : (
            <polygon points={`${-len},-4 ${len - 10},-4 ${len - 10},-10 ${len},0 ${len - 10},10 ${len - 10},4 ${-len},4`} />
          )
        ) : (
          <>
            <line x1={-len} y1="0" x2={len} y2="0" />
            <polyline points={`${len - 8},-6 ${len},0 ${len - 8},6`} />
            {heads === "both" && <polyline points={`${-len + 8},-6 ${-len},0 ${-len + 8},6`} />}
            {/* Struck through: the step is blocked (as printed). */}
            {style === "blocked" && <path d="M -7 -7 L 7 7 M -7 7 L 7 -7" />}
          </>
        )}
      </g>
    </svg>
  );
}

/** "Chapter 7.1" over a class in a class map — a link to that section. */
function ChapterLink({ node }: { node: SchemeNode }) {
  if (!node.chapter) return null;
  const label = `Chapter ${node.chapter}`;
  return node.chapter_href ? (
    <a
      href={node.chapter_href}
      className="mb-1.5 rounded-sm font-sans text-body font-bold text-accent underline decoration-accent/30 underline-offset-[3px] transition-colors duration-150 ease-out-soft hover:decoration-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      {label}
    </a>
  ) : (
    <p className="mb-1.5 font-sans text-body font-bold text-ink">{label}</p>
  );
}

function Node({ node, svg }: { node: SchemeNode; svg: string | null }) {
  if (!svg) {
    // A lone symbol between structures ("=", "+") reads at structure-label size; words stay small.
    const symbol = node.text_en.trim().length <= 2;
    return (
      <p
        className={`prose-book max-w-[14rem] text-center font-sans ${symbol ? "text-2xl leading-none text-ink" : "text-meta text-ink-soft"}`}
        dangerouslySetInnerHTML={html(node.text_en)}
      />
    );
  }
  return (
    <div className="flex flex-col items-center text-center">
      <ChapterLink node={node} />
      <div className="structure max-w-full" role="img" aria-label={`Structure ${node.number || ""} ${node.name_en.replace(/<[^>]+>/g, "")}`} dangerouslySetInnerHTML={html(svg)} />
      {node.number && <p className="mt-1 font-sans text-note font-bold tabular-nums text-ink">{node.number}</p>}
      {node.name_en && (
        // A class in a class map is captioned like a heading; other molecules carry a quiet name.
        <p
          className={`prose-book max-w-[12rem] font-sans ${node.chapter ? "mt-1 text-note font-semibold text-ink" : "text-meta text-ink-soft"}`}
          dangerouslySetInnerHTML={html(node.name_en)}
        />
      )}
      {node.data_en.map((d) => (
        <p key={d} className="prose-book font-sans text-meta tabular-nums text-ink-soft" dangerouslySetInnerHTML={html(d)} />
      ))}
      {node.status === "verified" && node.cid && (
        <a
          href={`https://pubchem.ncbi.nlm.nih.gov/compound/${node.cid}`}
          target="_blank"
          rel="noreferrer"
          className="mt-1 font-sans text-meta text-ink-faint underline decoration-rule underline-offset-2 transition-colors duration-150 ease-out-soft hover:text-accent hover:decoration-accent"
        >
          PubChem {node.cid}
        </a>
      )}
    </div>
  );
}

/**
 * A reaction/metabolism/SAR scheme redrawn on the printed grid: molecules at structure-card scale,
 * arrows with their labels. Wide schemes scroll sideways inside their own box on small screens.
 */
export async function SchemeView({ scheme }: { scheme: SchemeData }) {
  const keys = Object.keys(scheme.nodes);
  const svgs = new Map(
    await Promise.all(keys.map(async (k) => [k, scheme.nodes[k].svg ? await getSvg(scheme.nodes[k].svg!, scheme.generic ? undefined : SCHEME_SCALE) : null] as const)),
  );
  if (scheme.toc) return <TocView scheme={scheme} svgs={svgs} />;

  // Structures only (a generic figure without arrows): wrap like the card rows instead of scrolling sideways.
  const hasArrows = scheme.grid.some((row) => row.some((c) => c && "arrow" in c));
  if (scheme.generic && !hasArrows) {
    const order = scheme.grid.flatMap((row) => row.flatMap((c) => (c && "node" in c ? [c.node] : [])));
    return (
      <div className="flex flex-wrap items-end justify-center gap-x-10 gap-y-10">
        {order.map((key) => (
          <div key={key} className="flex max-w-full justify-center">
            <Node node={scheme.nodes[key]} svg={svgs.get(key) ?? null} />
          </div>
        ))}
      </div>
    );
  }

  const grid = <SchemeGrid scheme={scheme} svgs={svgs} />;
  if (!scheme.classmap) return grid;

  return <ClassMap scheme={scheme} svgs={svgs} />;
}

/** The printed text block beside a class: bullets as a dashed list, "3,4-Dimethoxy:"-style lines as small heads. */
function Callout({ node, className = "" }: { node: SchemeNode; className?: string }) {
  if (!node.callout_en?.length) return null;
  return (
    <div className={`prose-book max-w-[16rem] text-left font-sans text-meta leading-snug text-ink-soft ${className}`}>
      {node.callout_en.map((l, i) =>
        l.bullet ? (
          <p key={i} className="relative mt-0.5 pl-3">
            <span aria-hidden className="absolute left-0 text-ink-faint">–</span>
            <span dangerouslySetInnerHTML={html(l.html)} />
          </p>
        ) : (
          <p
            key={i}
            className={`${i ? "mt-2" : ""} ${/:\s*$/.test(l.html.replace(/<[^>]+>/g, "")) ? "font-semibold text-ink" : ""}`}
            dangerouslySetInnerHTML={html(l.html)}
          />
        ),
      )}
    </div>
  );
}

/** A class-map cell: the molecule (or text) with its callout below or beside it, as printed. */
function ClassCell({ node, svg }: { node: SchemeNode; svg: string | null }) {
  const textOnly = !svg && !node.text_en;
  const side = node.callout_side ?? "below";
  const layout = side === "right" ? "flex-row items-start" : side === "left" ? "flex-row-reverse items-start" : "flex-col items-center";
  return (
    <div className={`flex gap-4 ${layout}`}>
      {!textOnly && <Node node={node} svg={svg} />}
      <Callout node={node} className={side === "below" && !textOnly ? "mt-1" : ""} />
    </div>
  );
}

/**
 * Class map: a parent structure (role "core") with arrows to the classes, each headed by a link to its section.
 * From sm up the printed positions (the spec grid's node cells, empty rows/columns dropped) with measured arrows;
 * on phones the parent, then the classes as a card list in chapter order, then any other elements.
 */
function ClassMap({ scheme, svgs }: { scheme: SchemeData; svgs: Map<string, string | null> }) {
  const isCore = (k: string) => k === "core" || scheme.nodes[k].role === "core";
  const arrowOf = (k: string) => (isCore(k) ? "none" : scheme.nodes[k].arrow ?? (scheme.nodes[k].chapter ? "out" : "none"));
  const cells = scheme.grid.flatMap((row, r) => row.flatMap((c, i) => (c && "node" in c ? [{ key: c.node, r, i }] : [])));
  const rows = [...new Set(cells.map((c) => c.r))].sort((a, b) => a - b);
  const cols = [...new Set(cells.map((c) => c.i))].sort((a, b) => a - b);
  const order = cells.map((c) => c.key);
  const byChapter = (a: string, b: string) => scheme.nodes[a].chapter!.localeCompare(scheme.nodes[b].chapter!, undefined, { numeric: true });
  const classes = order.filter((k) => !isCore(k) && scheme.nodes[k].chapter).sort(byChapter);
  const others = order.filter((k) => !isCore(k) && !scheme.nodes[k].chapter);
  const node = (k: string) => <Node node={scheme.nodes[k]} svg={svgs.get(k) ?? null} />;
  // Callout layouts need room: the printed arrangement only on wide screens and up to four columns (a two-page
  // spread merged into one has more); otherwise the reading-order card list, which never scrolls sideways.
  const radial = scheme.wide ? (cols.length <= 4 ? "hidden xl:block" : "hidden") : "hidden sm:block";
  const list = scheme.wide ? (cols.length <= 4 ? "xl:hidden" : "") : "sm:hidden";
  return (
    <>
      <div className={`${radial} overflow-x-auto`}>
        <div
          className="relative mx-auto grid w-max items-center justify-items-center gap-x-14 gap-y-14"
          style={{ gridTemplateColumns: `repeat(${cols.length}, auto)` }}
        >
          {cells.map((c) => (
            <div
              key={c.key}
              data-cm={isCore(c.key) ? "core" : "class"}
              data-arrow={arrowOf(c.key)}
              data-label={scheme.nodes[c.key].arrow_label_en ?? ""}
              style={{ gridRow: rows.indexOf(c.r) + 1, gridColumn: cols.indexOf(c.i) + 1 }}
            >
              <ClassCell node={scheme.nodes[c.key]} svg={svgs.get(c.key) ?? null} />
            </div>
          ))}
          <ClassMapArrows />
        </div>
      </div>
      <div className={list}>
        {order.filter(isCore).map((k) => (
          <div key={k} className="flex justify-center">{node(k)}</div>
        ))}
        {classes.length > 0 && (
          <ul className={`mt-6 grid gap-x-8 gap-y-10 border-t border-rule pt-6 ${scheme.wide ? "grid-cols-1 md:grid-cols-2" : "grid-cols-2"}`}>
            {classes.map((k) => (
              <li key={k} className="flex min-w-0 flex-col items-center">
                {scheme.nodes[k].arrow_label_en && (
                  <p className="mb-1 font-sans text-meta text-ink-faint" dangerouslySetInnerHTML={html(scheme.nodes[k].arrow_label_en!)} />
                )}
                <ClassCell node={scheme.nodes[k]} svg={svgs.get(k) ?? null} />
              </li>
            ))}
          </ul>
        )}
        {others.length > 0 && (
          <div className="mt-6 flex flex-wrap items-end justify-center gap-x-10 gap-y-8 border-t border-rule pt-6">
            {others.map((k) => (
              <div key={k} className="flex justify-center">
                <ClassCell node={scheme.nodes[k]} svg={svgs.get(k) ?? null} />
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function SchemeGrid({ scheme, svgs }: { scheme: SchemeData; svgs: Map<string, string | null> }) {
  // Explicit placement: cells spanning columns or rows (a long axis arrow) take their slots; nulls stay empty.
  const cols = Math.max(...scheme.grid.map((row) => row.reduce((n, c) => n + (c?.span ?? 1), 0)));

  return (
    <div className="overflow-x-auto" tabIndex={0} aria-label="Scheme (scrolls sideways on small screens)">
      <div className="mx-auto grid w-max items-center gap-x-4 gap-y-6" style={{ gridTemplateColumns: `repeat(${cols}, auto)` }}>
        {scheme.grid.flatMap((row, r) => {
          let col = 1;
          return row.map((cell, i) => {
            const at = col;
            col += cell?.span ?? 1;
            if (!cell) return null;
            const place = { gridColumn: `${at} / span ${cell.span ?? 1}`, gridRow: `${r + 1} / span ${cell.rows ?? 1}` };
            if ("node" in cell) {
              return (
                <div key={`${r}-${i}`} className="flex justify-center" style={place}>
                  <Node node={scheme.nodes[cell.node]} svg={svgs.get(cell.node) ?? null} />
                </div>
              );
            }
            const beside = cell.label_side === "right" || cell.label_side === "left";
            const long = (cell.rows ?? 1) > 1;
            return (
              <div
                key={`${r}-${i}`}
                className={`flex items-center gap-2 text-center text-ink-soft ${beside ? (cell.label_side === "left" ? "flex-row-reverse" : "flex-row") : "flex-col"} ${long ? "self-stretch" : ""}`}
                style={place}
              >
                {!beside && cell.label_en && <span className="prose-book max-w-[11rem] font-sans text-meta" dangerouslySetInnerHTML={html(cell.label_en)} />}
                <Arrow direction={cell.arrow} style={cell.style} heads={cell.heads} long={long} />
                {beside && cell.label_en && <span className="prose-book max-w-[9rem] text-left font-sans text-meta" dangerouslySetInnerHTML={html(cell.label_en)} />}
                {cell.label_below_en && <span className="prose-book max-w-[11rem] font-sans text-meta" dangerouslySetInnerHTML={html(cell.label_below_en)} />}
              </div>
            );
          });
        })}
      </div>
    </div>
  );
}

/** A card's drawing: the SVG structure, or a drawing cut from the restored page, shown as an ink mask so it takes
 * the text colour in every theme. */
function CardDrawing({ node, svg }: { node: SchemeNode; svg: string | null }) {
  if (node.image) {
    // Cut from the restored page at a larger drawing scale than the SVG structures: brought to the same bond length.
    const w = Math.round(node.image.width * 0.5);
    const h = Math.round(node.image.height * 0.5);
    const mask = `url(${node.image.src}) center / contain no-repeat`;
    return (
      <span
        role="img"
        aria-label={`Structure: ${(node.name_en || "").replace(/<[^>]+>/g, "")}`}
        className="block max-w-full bg-ink"
        style={{ width: w, height: h, aspectRatio: `${w} / ${h}`, mask, WebkitMask: mask }}
      />
    );
  }
  if (!svg) return null;
  return <span className="structure block max-w-full [&_svg]:h-auto [&_svg]:max-w-full" dangerouslySetInnerHTML={html(svg)} />;
}

/** One chapter of the visual table of contents: the whole card is the link. */
function TocCard({ id, scheme, svgs }: { id: string; scheme: SchemeData; svgs: Map<string, string | null> }) {
  const node = scheme.nodes[id];
  const extras = Object.keys(scheme.nodes).filter((k) => scheme.nodes[k].of === id);
  const body = (
    <>
      <span className="font-sans text-note font-bold text-accent">Chapter {node.chapter}</span>
      <span className="my-2 flex flex-1 flex-col items-center justify-center gap-2">
        {[id, ...extras].map((k) => (
          <CardDrawing key={k} node={scheme.nodes[k]} svg={svgs.get(k) ?? null} />
        ))}
      </span>
      {node.name_en && <span className="font-sans text-meta leading-snug text-ink text-balance" dangerouslySetInnerHTML={html(node.name_en)} />}
    </>
  );
  const cls =
    "flex h-full flex-col items-center rounded-md bg-tint px-3 pb-3 pt-2.5 text-center transition-colors duration-150 ease-out-soft";
  return node.chapter_href ? (
    <a
      href={node.chapter_href}
      className={`${cls} hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent`}
    >
      {body}
    </a>
  ) : (
    <div className={cls}>{body}</div>
  );
}

/** The visual table of contents: the printed flow at the top (cards, notes, arrows), then the chapter cards. */
function TocView({ scheme, svgs }: { scheme: SchemeData; svgs: Map<string, string | null> }) {
  const toc = scheme.toc!;
  return (
    <div className="font-sans">
      {toc.head.map((row, r) => (
        <div key={r} className="mb-3 flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
          {row.map((item, i) =>
            "box" in item ? (
              // A titled group without a chapter of its own (the parent compounds): drawings with their names.
              <div key={i} className="rounded-md bg-tint px-5 pb-3 pt-2.5 text-center">
                <p className="font-sans text-note font-bold text-ink">{item.box.title_en}</p>
                <div className="mt-2 flex flex-wrap items-end justify-center gap-x-8 gap-y-3">
                  {item.box.members.map((k) => (
                    <div key={k} className="flex flex-col items-center">
                      <CardDrawing node={scheme.nodes[k]} svg={svgs.get(k) ?? null} />
                      <span className="mt-1 font-sans text-meta text-ink" dangerouslySetInnerHTML={html(scheme.nodes[k].name_en)} />
                    </div>
                  ))}
                </div>
              </div>
            ) : "card" in item ? (
              <div key={i} className="w-44">
                <TocCard id={item.card} scheme={scheme} svgs={svgs} />
              </div>
            ) : "text" in item ? (
              <p
                key={i}
                className="prose-book max-w-[13rem] text-center text-note text-ink-soft"
                dangerouslySetInnerHTML={html(scheme.nodes[item.text].text_en)}
              />
            ) : (
              <div key={i} className="flex items-center gap-2 text-ink-soft">
                <Arrow direction={item.arrow} style="open" />
                {item.label_en && <span className="text-meta" dangerouslySetInnerHTML={html(item.label_en)} />}
              </div>
            ),
          )}
        </div>
      ))}
      {toc.groups.map((group, g) => (
        <div key={g} className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {group.map((id) => (
            <TocCard key={id} id={id} scheme={scheme} svgs={svgs} />
          ))}
        </div>
      ))}
    </div>
  );
}

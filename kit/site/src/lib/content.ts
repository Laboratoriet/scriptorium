import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

// Content is produced by scripts/build_content.py (see the repo root).
// HTML strings in here are generated from our own verified Markdown, never user input.

const CONTENT_DIR = path.join(process.cwd(), "content");
const PUBLIC_DIR = path.join(process.cwd(), "public");

export type SideNote = { n: number; html: string };

/** page: printed page number — arabic, or roman ("XV") in the front matter; null for unnumbered pages. */
type BlockBase = { page: number | string | null; tns: SideNote[] };

export type HeadingBlock = BlockBase & {
  type: "heading";
  level: number;
  number: string | null;
  anchor: string | null;
  en: string;
  de: string;
};

export type ParagraphBlock = BlockBase & { type: "paragraph"; en: string; de: string };

export type TableBlock = BlockBase & {
  type: "table";
  en: string;
  de: string;
  caption_en?: string;
  caption_de?: string;
  /** Crop of the printed table, for checking the transcription. */
  original?: { src: string; width: number; height: number };
};

export type Compound = {
  key: string;
  number: string;
  svg: string;
  names_en: string[];
  names_de: string[];
  smiles: string;
  /** PubChem entry the drawing was checked against; absent for compounds the book doesn't name. */
  cid?: number;
  /** "read-twice": no database to check against — two blind readings of the drawing agreed. */
  status: "verified" | "corrected" | "read-twice";
  /** "pubchem": no name printed with the drawing; this one is PubChem's (see scripts/name_compounds.py). */
  name_source?: "pubchem";
};

type Axis = { de?: string | null; en?: string | null; min?: number; max?: number; ticks?: number[] };

export type ChartData = {
  id: string;
  type?: "grouped-bar" | "line";
  title: { de: string; en: string };
  x_axis?: Axis | null;
  y_axis: Axis & { min: number; max: number; ticks: number[] };
  series: { key: string; de: string; en: string }[];
  /** grouped-bar: one value per series key (null where the book has no bar). */
  categories?: ({ de: string; en: string } & Record<string, number | string | object | null>)[];
  /** line: [x, y] points per series key. */
  points?: Record<string, [number, number][]>;
  /** The values are printed on the chart (transcribed), not measured off it. */
  values_printed?: boolean;
  note_en?: string;
};

export type SchemeNode = {
  number: string;
  /** Class maps: the section this class is treated in ("7.1") and a link to it. */
  chapter?: string;
  chapter_href?: string | null;
  /** Class maps: "core" = the parent structure; arrow from ("out", default for classes) or to ("in") the core. */
  role?: "core";
  arrow?: "out" | "in" | "none";
  arrow_label_en?: string;
  /** Structure–activity summaries: the printed text block beside this class, line by line ("- " lines are bullets). */
  callout_en?: { bullet: boolean; html: string }[];
  callout_side?: "right" | "left" | "below";
  /** Visual table of contents: a drawing cut from the restored page (ink mask), and extra drawings of one card. */
  image?: { src: string; width: number; height: number };
  of?: string;
  name_en: string;
  name_de: string;
  data_en: string[];
  text_en: string;
  text_de: string;
  svg?: string;
  status?: "verified" | "mismatch" | "not-found" | "unnamed" | "generic";
  cid?: number;
};

export type SchemeCell =
  | { node: string; span?: number; rows?: number }
  | {
      arrow: string;
      span?: number;
      rows?: number;
      style?: "line" | "open" | "blocked";
      heads?: "both";
      label_side?: "right" | "left" | null;
      label_en: string;
      label_below_en: string;
      label_de: string;
      label_below_de: string;
    }
  | null;

export type SchemeData = {
  nodes: Record<string, SchemeNode>;
  grid: SchemeCell[][];
  /** A class map: parent structure with arrows to the classes, each linked to its chapter section. */
  classmap?: boolean;
  /** Visual table of contents: head rows (cards, notes, arrows) and groups of chapter cards. */
  toc?: {
    head: ({ card: string } | { text: string } | { arrow: string; label_en?: string } | { box: { title_en: string; members: string[] } })[][];
    groups: string[][];
  } | null;
  /** Dense callout layout: takes the margin column too on wide screens. */
  wide?: boolean;
  pilot?: boolean;
  checked?: boolean;
  generic?: boolean;
};

export type FigureBlock = BlockBase & {
  type: "figure";
  id: string;
  kind: "structure" | "chart" | "advert" | "photo" | "scheme" | "diagram" | string;
  label: string;
  caption_en: string;
  caption_de: string;
  tn_marker: string;
  compounds?: Compound[];
  chart?: ChartData;
  scheme?: SchemeData;
  /** A printed document given as English text (figures/translations/<id>.md); the scan behind the toggle. */
  document_en?: string;
  original?: { src: string; width: number; height: number };
  /** Cleaned and upscaled version of the printed image (shown instead of the scan, which stays available). */
  /** method "cleanup": contrast and sharpening only (nothing redrawn); "upscale": cleaned and upscaled. */
  /** A simple schematic redrawn by hand as SVG (public path). */
  illustration?: string;
  /** Second half of a two-page figure that is redrawn as one: points back to it. */
  merged_into?: { id: string; label: string };
  restored?: { src: string; width: number; height: number; method?: "cleanup" | "upscale" };
  /** Structures/scheme/chart not redrawn yet — the printed original is shown. */
  pending?: boolean;
  partial?: boolean;
  /** Columns of a table printed as an image: cards grouped under headings. */
  groups?: { en: string; de: string; compounds: string[] }[];
  labels_en?: string[];
};

/** href: verified DOI (link "doi") or a URL printed in the entry (link "url") — see scripts/link_references.py. */
export type ReferencesBlock = BlockBase & {
  type: "references";
  scope: number;
  refs: { n: number; html: string; href?: string; link?: "doi" | "url" }[];
};

export type FootnoteBlock = BlockBase & { type: "footnote"; id: string; en: string; de: string };

export type Block =
  | HeadingBlock
  | ParagraphBlock
  | TableBlock
  | FigureBlock
  | ReferencesBlock
  | FootnoteBlock;

/** A reading unit: a chapter, or a group of front-matter chapters (see source/units.yaml). */
export type Chapter = {
  slug: string;
  title_de: string;
  title_en: string;
  first: number;
  last: number;
  blocks: Block[];
};

export type TocEntry = {
  id: string;
  kind: "front" | "chapter" | "section" | "excursus" | "back";
  page: string;
  de: string;
  en: string | null;
  unit: string | null;
  available: boolean;
};

export async function getChapter(slug: string): Promise<Chapter> {
  return JSON.parse(await readFile(path.join(CONTENT_DIR, "units", `${slug}.json`), "utf8"));
}

export async function getToc(): Promise<TocEntry[]> {
  // A new book has no contents built yet: an empty site still builds.
  return JSON.parse(await readFile(path.join(CONTENT_DIR, "toc.json"), "utf8").catch(() => "[]"));
}

/** Slugs of built units, in reading order. */
export async function getAvailableChapters(): Promise<string[]> {
  const files = await readdir(path.join(CONTENT_DIR, "units")).catch(() => [] as string[]);
  const units = await Promise.all(files.map((f) => getChapter(f.replace(/\.json$/, ""))));
  return units.sort((a, b) => a.first - b.first).map((u) => u.slug);
}

export type UnitLink = { slug: string; title: string; number: string | null };

/** The units before and after this one, in the book's order (as the table of contents lists them). */
export async function getNeighbours(slug: string): Promise<{ prev: UnitLink | null; next: UnitLink | null }> {
  const toc = await getToc();
  const order: string[] = [];
  for (const e of toc) if (e.unit && e.available && !order.includes(e.unit)) order.push(e.unit);
  const i = order.indexOf(slug);
  const link = async (s: string | undefined): Promise<UnitLink | null> => {
    if (!s) return null;
    const c = await getChapter(s);
    return { slug: s, title: c.title_en || c.title_de, number: /^\d+$/.test(s) ? s : null };
  };
  return { prev: await link(order[i - 1]), next: await link(order[i + 1]) };
}

/** Structure SVGs are inlined so they inherit the theme's text colour. */
/** Structures are drawn at the book's bond length; on screen they read better a size up. */
const STRUCTURE_SCALE = 1.4;

export async function getSvg(publicPath: string, scale = STRUCTURE_SCALE): Promise<string> {
  const svg = await readFile(path.join(PUBLIC_DIR, publicPath), "utf8");
  // Scale the rendered size only; the viewBox keeps the drawing, so every molecule grows alike.
  return svg.replace(/(width|height)='(\d+(?:\.\d+)?)px'/g, (_, dim, n) => `${dim}='${Math.round(Number(n) * scale)}px'`);
}

/** For "Go to page N" in search: each unit's printed page range and the pages that have an anchor (#page-N). */
export type PageUnit = { slug: string; title: string; first: number; last: number; pages: number[]; figures: string[] };

export async function getPageIndex(): Promise<PageUnit[]> {
  const slugs = await getAvailableChapters();
  const units = await Promise.all(slugs.map((s) => getChapter(s)));
  return units.map((u) => ({
    slug: u.slug,
    title: u.title_en || u.title_de,
    first: u.first,
    last: u.last,
    pages: [...new Set(u.blocks.map((b) => b.page).filter((p): p is number => typeof p === "number"))].sort((a, b) => a - b),
    // Figure ids (p0121-2): the search jumps straight to one.
    figures: u.blocks.flatMap((b) => (b.type === "figure" ? [b.id] : [])),
  }));
}

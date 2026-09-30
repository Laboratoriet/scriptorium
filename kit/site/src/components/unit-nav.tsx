import Link from "next/link";
import type { UnitLink } from "@/lib/content";

function Card({ unit, dir }: { unit: UnitLink; dir: "prev" | "next" }) {
  const next = dir === "next";
  return (
    <Link
      href={`/chapter/${unit.slug}/`}
      rel={dir}
      className={`group flex min-h-20 flex-col justify-center gap-1 rounded-md border border-rule px-4 py-3 transition-colors duration-150 ease-out-soft hover:border-accent/50 hover:bg-tint focus-visible:bg-tint ${next ? "items-end text-right sm:col-start-2" : "items-start text-left"}`}
    >
      <span className="font-sans text-meta text-ink-faint transition-colors duration-150 ease-out-soft group-hover:text-accent">
        {next ? "Next →" : "← Previous"}
      </span>
      <span className="font-serif text-body leading-snug text-ink text-balance">
        {unit.number && <span className="mr-2 font-sans tabular-nums text-ink-faint">{unit.number}</span>}
        {unit.title}
      </span>
    </Link>
  );
}

/** Previous / next unit at the end of a chapter, so reading on doesn't need the contents page. */
export function UnitNav({ prev, next }: { prev: UnitLink | null; next: UnitLink | null }) {
  if (!prev && !next) return null;
  return (
    <nav aria-label="Previous and next section" className="mt-16 grid gap-3 border-t border-rule pt-8 sm:grid-cols-2" data-pagefind-ignore="all">
      {prev && <Card unit={prev} dir="prev" />}
      {next && <Card unit={next} dir="next" />}
    </nav>
  );
}

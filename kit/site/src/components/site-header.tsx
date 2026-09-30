import Link from "next/link";
import BOOK from "@/book.json";
import { getPageIndex } from "@/lib/content";
import { SearchDialog } from "@/components/search-dialog";
import { ShowAllGerman } from "@/components/show-all-german";
import { ShowNotes } from "@/components/show-notes";
import { ThemeToggle } from "@/components/theme-toggle";

export async function SiteHeader() {
  const pageIndex = await getPageIndex();
  return (
    <header className="sticky top-0 z-20 border-b border-rule bg-paper/90 backdrop-blur supports-[backdrop-filter]:bg-paper/75">
      <div className="mx-auto flex h-14 max-w-[76rem] items-center justify-between gap-4 px-4">
        <Link
          href="/"
          className="truncate font-sans text-note font-semibold tracking-tight text-ink hover:text-accent"
        >
          {BOOK.title} <span className="hidden font-normal text-ink-faint sm:inline">— {BOOK.subtitle}</span>
        </Link>
        <nav className="flex items-center gap-1 font-sans text-meta" aria-label="Reading options">
          <SearchDialog pageIndex={pageIndex} />
          <ShowAllGerman />
          <ShowNotes />
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}

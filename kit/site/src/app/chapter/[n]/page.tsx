import type { Metadata } from "next";
import { ChapterBody } from "@/components/chapter-body";
import { SideNoteStacker } from "@/components/side-note-stacker";
import { UnitNav } from "@/components/unit-nav";
import { getAvailableChapters, getChapter, getNeighbours } from "@/lib/content";

export async function generateStaticParams() {
  const chapters = await getAvailableChapters();
  return chapters.map((n) => ({ n }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: PageProps<"/chapter/[n]">): Promise<Metadata> {
  const { n } = await params;
  const chapter = await getChapter(n);
  const title = chapter.title_en || chapter.title_de;
  return { title: /^\d+$/.test(n) ? `${n}. ${title}` : title };
}

export default async function ChapterPage({ params }: PageProps<"/chapter/[n]">) {
  const { n } = await params;
  const [chapter, neighbours] = await Promise.all([getChapter(n), getNeighbours(n)]);

  return (
    <main className="mx-auto max-w-[76rem] px-4 pb-24 pt-10 md:pt-14" data-pagefind-body>
      <ChapterBody chapter={chapter} />
      <SideNoteStacker />
      {/* Aligned with the reading column (gutter 3.5rem + the row gap: 1.5rem on md, 2.5rem on xl). */}
      <div className="md:ml-[5rem] md:max-w-[42rem] xl:ml-[6rem]">
        <UnitNav {...neighbours} />
      </div>
    </main>
  );
}

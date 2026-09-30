import type { Metadata } from "next";
import { Source_Sans_3, Source_Serif_4 } from "next/font/google";
import { SiteHeader } from "@/components/site-header";
import BOOK from "@/book.json";
import "./globals.css";

const textFont = Source_Serif_4({
  variable: "--font-text",
  subsets: ["latin", "latin-ext", "greek"],
  style: ["normal", "italic"],
});

const uiFont = Source_Sans_3({
  variable: "--font-ui",
  subsets: ["latin", "latin-ext", "greek"],
});

export const metadata: Metadata = {
  title: { default: `${BOOK.title} — ${BOOK.subtitle}`, template: `%s · ${BOOK.title}` },
  description: BOOK.description,
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${textFont.variable} ${uiFont.variable} antialiased`} suppressHydrationWarning>
      <head>
        {/* Before first paint: the reader's theme, "Hide notes" and collapsed-contents choices, so nothing flashes or jumps. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var d=document.documentElement;var th=localStorage.getItem("theme");if(th==="light"||th==="paper"||th==="dark")d.setAttribute("data-theme",th);if(localStorage.getItem("notes-hidden")==="1")d.setAttribute("data-notes-hidden","");var t=localStorage.getItem("toc-collapsed");if(t)d.setAttribute("data-toc-collapsed",t)}catch(e){}`,
          }}
        />
      </head>
      <body className="min-h-dvh font-serif text-body">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}

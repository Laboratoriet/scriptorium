// Source-language search index (the language in src/book.json): the same pages with the English text left out and the German panels in.
// The site searches it only while German is shown (see search-dialog.tsx). Run after `pagefind --site out`.
import { cpSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
const BOOK = JSON.parse(readFileSync(new URL("./src/book.json", import.meta.url), "utf8"));

const tmp = mkdtempSync(path.join(tmpdir(), "pagefind-de-"));
function* htmlFiles(dir) {
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) { if (!name.startsWith("pagefind")) yield* htmlFiles(p); }
    else if (name.endsWith(".html")) yield p;
  }
}
for (const file of htmlFiles("out")) {
  const html = readFileSync(file, "utf8")
    .replaceAll('data-search="en"', 'data-pagefind-ignore="all"')
    .replaceAll('data-pagefind-ignore="all" data-search="de"', 'data-search="de"')
    .replace('<html lang="en"', `<html lang="${BOOK.source.code}"`);
  const target = path.join(tmp, path.relative("out", file));
  cpSync(file, target, { recursive: true });
  writeFileSync(target, html);
}
execFileSync("pagefind", ["--site", tmp, "--output-path", "out/pagefind-de"], { stdio: "inherit" });
rmSync(tmp, { recursive: true, force: true });

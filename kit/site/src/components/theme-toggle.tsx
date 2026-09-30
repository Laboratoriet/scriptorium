"use client";

import { useEffect, useState } from "react";

type Theme = "system" | "light" | "paper" | "dark";
const ORDER: Theme[] = ["system", "light", "paper", "dark"];
/** Auto follows the system (white or dark); Paper is a warm book tone. */
const LABEL: Record<Theme, string> = { system: "Auto", light: "White", paper: "Paper", dark: "Dark" };

function apply(theme: Theme) {
  if (theme === "system") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", theme);
}

/** Cycles Auto → White → Paper → Dark. Remembered per browser; the layout applies it before first paint. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("theme") as Theme | null;
      if (saved && ORDER.includes(saved)) {
        setTheme(saved);
        apply(saved);
      }
    } catch {
      // Storage unavailable (private mode): stay on system theme.
    }
  }, []);

  function cycle() {
    const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
    setTheme(next);
    apply(next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Ignore: the theme still applies for this visit.
    }
  }

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Theme: ${LABEL[theme]}. Change theme`}
      className="inline-flex h-9 min-w-14 items-center justify-center rounded-sm px-2.5 text-ink-soft transition-colors duration-150 ease-out-soft hover:bg-tint hover:text-ink"
    >
      {LABEL[theme]}
    </button>
  );
}

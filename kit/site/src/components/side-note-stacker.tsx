"use client";

import { useEffect } from "react";

const GAP = 12; // px between two stacked notes

/**
 * Margin notes sit beside the paragraph they belong to, in a zero-height column — so a long note can run into the
 * next one. After layout, each note is pushed down just far enough to clear the one above it (xl only, where the
 * margin column exists). The main text never moves, so there is no layout shift.
 */
export function SideNoteStacker() {
  useEffect(() => {
    const wide = window.matchMedia("(min-width: 80rem)");
    let frame = 0;

    const stack = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const lists = Array.from(document.querySelectorAll<HTMLElement>("[data-sidenotes] > ol"));
        for (const el of lists) el.style.transform = "";
        if (!wide.matches) return;
        let prevBottom = -Infinity;
        for (const el of lists) {
          const rect = el.getBoundingClientRect();
          const shift = Math.max(0, prevBottom + GAP - rect.top);
          if (shift) el.style.transform = `translateY(${shift}px)`;
          prevBottom = rect.bottom + shift;
        }
      });
    };

    stack();
    void document.fonts?.ready.then(stack);
    // Row heights change when German panels open, images load, or the window resizes.
    const observer = new ResizeObserver(stack);
    const main = document.querySelector("main");
    if (main) observer.observe(main);
    wide.addEventListener("change", stack);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      wide.removeEventListener("change", stack);
    };
  }, []);

  return null;
}

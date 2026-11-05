"use client";

import { useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

const WIDTH = 288; // w-72
const GAP = 8;

/** Tooltip rendered into <body> with fixed position, so cards with `overflow-hidden` never clip it.
 *  Opens above the anchor, or below when there is no room; shown on hover and keyboard focus. */
export function ChipTooltip({ children, tip }: { children: ReactNode; tip: ReactNode }) {
  const anchor = useRef<HTMLSpanElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number; above: boolean } | null>(null);

  const show = () => {
    const r = anchor.current?.getBoundingClientRect();
    if (!r) return;
    const left = Math.max(GAP, Math.min(r.left, window.innerWidth - WIDTH - GAP));
    const above = r.top > 160;
    setPos({ left, top: above ? r.top - GAP : r.bottom + GAP, above });
  };
  const hide = () => setPos(null);

  return (
    <span
      ref={anchor}
      className="relative inline-flex align-middle"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {pos &&
        createPortal(
          <span
            role="tooltip"
            style={{ left: pos.left, top: pos.top, width: WIDTH, transform: pos.above ? "translateY(-100%)" : undefined }}
            className="pointer-events-none fixed z-50 rounded-lg bg-ink p-3 text-sm font-normal text-white shadow-lg"
          >
            {tip}
          </span>,
          document.body,
        )}
    </span>
  );
}

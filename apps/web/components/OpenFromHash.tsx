"use client";

import { useEffect } from "react";

/** Deep links like /leistungen#pflegegeld (from Mein Fall, bundles, chat): open every enclosing <details> (e.g.
 *  "Weitere Leistungen") AND the target card itself, scroll to it and highlight it briefly. */
export function OpenFromHash() {
  useEffect(() => {
    const run = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      if (!id) return;
      const el = document.getElementById(id);
      if (!el) return;
      for (let p = el.parentElement; p; p = p.parentElement) if (p instanceof HTMLDetailsElement) p.open = true;
      const own = el instanceof HTMLDetailsElement ? el : el.querySelector("details");
      if (own) own.open = true;
      el.scrollIntoView({ block: "start", behavior: "smooth" });
      el.classList.add("ring-2", "ring-accent", "rounded-xl");
      window.setTimeout(() => el.classList.remove("ring-2", "ring-accent"), 2500);
    };
    run();
    const t = window.setTimeout(run, 300); // after client-side navigation the content may render a tick later
    window.addEventListener("hashchange", run);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("hashchange", run);
    };
  }, []);
  return null;
}

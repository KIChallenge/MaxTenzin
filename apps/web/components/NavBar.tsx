"use client";
import { ChevronDown } from "lucide-react";
// Primary navigation: the current page is marked (wayfinding); reference pages are grouped under "Nachschlagen".
import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const MAIN = [
  ["/", "Übersicht"],
  ["/dokumente", "Dokumente"],
  ["/leistungen", "Leistungen"],
  ["/fall", "Mein Fall"],
  ["/vorsorge", "Vorsorge"],
  ["/transparenz", "Transparenz"],
] as const;
const LOOKUP = [
  ["/stellen", "Zuständige Stellen"],
  ["/medikamente", "Medikamente"],
  ["/recht", "Rechtsgrundlagen"],
] as const;

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  if (href === "/leistungen") return pathname.startsWith("/leistungen") || pathname.startsWith("/forms");
  return pathname.startsWith(href);
}

export function NavBar() {
  const pathname = usePathname();
  const menu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    if (menu.current) menu.current.open = false;
  }, [pathname]);
  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (menu.current && !menu.current.contains(e.target as Node)) menu.current.open = false;
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);
  const lookupActive = LOOKUP.some(([href]) => isActive(pathname, href));
  const item = (active: boolean) =>
    `block rounded-md px-2.5 py-1.5 text-[0.9375rem] whitespace-nowrap transition-colors ${
      active ? "bg-accent-soft font-semibold text-accent-strong" : "text-muted hover:bg-neutral-soft hover:text-ink"
    }`;
  return (
    <nav aria-label="Hauptnavigation">
      <ul className="flex flex-wrap items-center gap-0.5">
        {MAIN.map(([href, label]) => (
          <li key={href}>
            <Link href={href} className={item(isActive(pathname, href))} aria-current={isActive(pathname, href) ? "page" : undefined}>
              {label}
            </Link>
          </li>
        ))}
        <li>
          <details ref={menu} className="relative">
            <summary className={`${item(lookupActive)} cursor-pointer list-none [&::-webkit-details-marker]:hidden`}>
              <span className="inline-flex items-center gap-0.5">Nachschlagen <ChevronDown className="h-4 w-4" aria-hidden /></span>
            </summary>
            <ul className="absolute left-0 z-40 mt-1 min-w-52 rounded-lg border border-line bg-surface p-1 shadow-lg">
              {LOOKUP.map(([href, label]) => (
                <li key={href}>
                  <Link href={href} className={item(isActive(pathname, href))} aria-current={isActive(pathname, href) ? "page" : undefined}>
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </details>
        </li>
      </ul>
    </nav>
  );
}

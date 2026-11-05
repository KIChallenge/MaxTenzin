"use client";
// Accessible typeahead (combobox pattern) over the medication or legal search API.
// Debounced (250 ms, ≥ 3 chars): every lookup is a real, audited API call.
import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { LegalHit, Medication } from "@/lib/types";

type Option = { key: string; label: string; sub: string; href: string };

const SOURCES = {
  medications: async (q: string, signal: AbortSignal): Promise<Option[]> => {
    const r = await bffWithSignal<Medication[]>(`/api/medications/search?q=${encodeURIComponent(q)}&limit=8`, signal);
    return r.map((m) => ({ key: m.pharma_nr, label: m.name, sub: `${m.pack} · ${boxLabel(m.box)}`, href: `/medikamente?q=${encodeURIComponent(m.name)}` }));
  },
  legal: async (q: string, signal: AbortSignal): Promise<Option[]> => {
    const r = await bffWithSignal<LegalHit[]>(`/api/legal/search?q=${encodeURIComponent(q)}&limit=8`, signal);
    return r.map((h) => ({
      key: h.paragraph.doc_id,
      label: `§ ${h.paragraph.nr} ${h.paragraph.law} – ${h.paragraph.heading}`,
      sub: h.paragraph.law_title,
      href: `/recht?law=${encodeURIComponent(h.paragraph.law_key)}&nr=${encodeURIComponent(h.paragraph.nr)}`,
    }));
  },
};

async function bffWithSignal<T>(path: string, signal: AbortSignal): Promise<T> {
  const res = await fetch(`/bff${path}`, { signal, cache: "no-store" });
  if (!res.ok) return [] as T;
  return (await res.json()) as T;
}
function boxLabel(b: string) {
  return { G: "Grüner Bereich", Y: "Gelber Bereich", R: "Roter Bereich" }[b] ?? b;
}

export function Autocomplete({
  source,
  name,
  label,
  defaultValue,
  placeholder,
}: {
  source: keyof typeof SOURCES;
  name: string;
  label: string;
  defaultValue?: string;
  placeholder?: string;
}) {
  const [value, setValue] = useState(defaultValue ?? "");
  const [options, setOptions] = useState<Option[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const typed = useRef(false);
  const router = useRouter();
  const id = useId();
  const listId = `${id}-list`;

  useEffect(() => {
    if (!typed.current) return;
    const q = value.trim();
    if (q.length < 3) {
      setOptions([]);
      setOpen(false);
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const opts = await SOURCES[source](q, ctrl.signal);
        setOptions(opts);
        setOpen(true);
        setActive(-1);
      } catch {
        /* aborted */
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [value, source]);

  function choose(o: Option) {
    setOpen(false);
    setValue(o.label);
    router.push(o.href);
  }

  return (
    <div className="relative flex flex-1 flex-col gap-1">
      <label htmlFor={id} className="font-semibold">
        {label}
      </label>
      <input
        id={id}
        name={name}
        className="input"
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        onChange={(e) => {
          typed.current = true;
          setValue(e.target.value);
        }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onFocus={() => options.length && setOpen(true)}
        onKeyDown={(e) => {
          if (!open || options.length === 0) return;
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, options.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter" && active >= 0) {
            e.preventDefault();
            choose(options[active]);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open && (
        <ul
          id={listId}
          role="listbox"
          className="absolute top-full right-0 left-0 z-30 mt-1 max-h-80 overflow-y-auto rounded-lg border border-line bg-surface shadow-lg"
        >
          {options.length === 0 && !loading && <li className="px-3 py-2 text-muted">Keine Treffer.</li>}
          {options.map((o, i) => (
            <li
              key={o.key}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(o);
              }}
              onMouseEnter={() => setActive(i)}
              className={`cursor-pointer px-3 py-2 ${i === active ? "bg-accent-soft" : ""}`}
            >
              <span className="block font-semibold">{o.label}</span>
              <span className="block text-sm text-muted">{o.sub}</span>
            </li>
          ))}
        </ul>
      )}
      <span aria-live="polite" className="sr-only">
        {open ? `${options.length} Vorschläge` : ""}
      </span>
    </div>
  );
}

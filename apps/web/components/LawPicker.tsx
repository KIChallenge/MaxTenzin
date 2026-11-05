"use client";
// Searchable law picker (combobox): type an abbreviation or part of the full title.
import { useId, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { type Law, lawByKey, matchLaws } from "@/lib/laws";

export function LawPicker({ name, defaultKey, allowAll = false }: { name: string; defaultKey?: string; allowAll?: boolean }) {
  const [selected, setSelected] = useState<Law | undefined>(lawByKey(defaultKey));
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const id = useId();
  const listId = `${id}-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const options: (Law | null)[] = [...(allowAll && !query ? [null] : []), ...matchLaws(query)];

  function choose(l: Law | null) {
    setSelected(l ?? undefined);
    setQuery("");
    setOpen(false);
  }

  return (
    <div className="relative flex flex-col gap-1">
      <label htmlFor={id} className="font-semibold">
        Gesetz / Richtlinie
      </label>
      <input type="hidden" name={name} value={selected?.key ?? ""} />
      <div className="relative">
        <input
          ref={inputRef}
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open ? `${listId}-${active}` : undefined}
          autoComplete="off"
          className="input pr-8"
          placeholder={allowAll ? "Alle Gesetze" : "z. B. BPGG oder Pflegegeld"}
          value={open ? query : selected ? `${selected.abbr} – ${selected.title}` : ""}
          onFocus={() => {
            setOpen(true);
            setActive(0);
          }}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setActive(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setOpen(true);
              setActive((a) => Math.min(a + 1, options.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === "Enter" && open && options.length) {
              e.preventDefault();
              choose(options[active]);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
        />
        <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
      </div>
      {open && (
        <ul
          id={listId}
          role="listbox"
          className="absolute top-full right-0 left-0 z-30 mt-1 max-h-80 min-w-80 overflow-y-auto rounded-lg border border-line bg-surface p-1 shadow-lg"
        >
          {options.length === 0 && <li className="px-3 py-2 text-muted">Kein Gesetz gefunden.</li>}
          {options.map((l, i) => (
            <li
              key={l?.key ?? "__all"}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(l);
              }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-start gap-2 rounded-md px-2.5 py-1.5 ${i === active ? "bg-accent-soft" : ""}`}
            >
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{l ? l.abbr : "Alle Gesetze"}</span>
                {l && <span className="block text-sm leading-snug text-muted">{l.title}</span>}
              </span>
              {(l?.key ?? "") === (selected?.key ?? "") && <Check className="mt-1 h-4 w-4 text-accent" aria-hidden />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

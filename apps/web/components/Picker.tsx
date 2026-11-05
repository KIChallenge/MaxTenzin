"use client";
// Searchable select (combobox) used for law, paragraph and topic pickers – same look as the person menu.
import { useId, useState } from "react";
import { Check, ChevronDown } from "lucide-react";

export type PickerOption = { value: string; label: string; sub?: string; search?: string };

const norm = (s: string) => s.toLowerCase().replace(/[\s_\-.§]/g, "").replace(/ö/g, "oe").replace(/ä/g, "ae").replace(/ü/g, "ue");

export function Picker({
  name,
  label,
  options,
  value,
  onChange,
  placeholder,
  emptyLabel,
  className = "",
  disabled = false,
}: {
  name?: string;
  label: string;
  options: PickerOption[];
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  /** If set, an entry with value "" is offered first (e.g. "Alle Gesetze"). */
  emptyLabel?: string;
  className?: string;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const id = useId();
  const listId = `${id}-list`;
  const selected = options.find((o) => o.value === value);
  const q = norm(query);
  const all: PickerOption[] = [...(emptyLabel && !q ? [{ value: "", label: emptyLabel }] : []), ...options];
  const shown = (q ? all.filter((o) => norm(`${o.label} ${o.sub ?? ""} ${o.search ?? ""}`).includes(q)) : all).slice(0, 200);

  function choose(o: PickerOption) {
    onChange(o.value);
    setQuery("");
    setOpen(false);
  }

  return (
    <div className={`relative flex flex-col gap-1 ${className}`}>
      <label htmlFor={id} className="font-semibold">
        {label}
      </label>
      {name && <input type="hidden" name={name} value={value} />}
      <div className="relative">
        <input
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={open && shown[active] ? `${listId}-${active}` : undefined}
          autoComplete="off"
          disabled={disabled}
          className="input pr-8"
          placeholder={selected ? undefined : (placeholder ?? emptyLabel)}
          value={open ? query : selected ? `${selected.label}${selected.sub ? ` – ${selected.sub}` : ""}` : ""}
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
              setActive((a) => Math.min(a + 1, shown.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === "Enter" && open && shown[active]) {
              e.preventDefault();
              choose(shown[active]);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
        />
        <ChevronDown className="pointer-events-none absolute top-1/2 right-2.5 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
      </div>
      {open && (
        <ul id={listId} role="listbox" className="absolute top-full right-0 left-0 z-30 mt-1 max-h-80 min-w-64 overflow-y-auto rounded-lg border border-line bg-surface p-1 shadow-lg">
          {shown.length === 0 && <li className="px-3 py-2 text-muted">Nichts gefunden.</li>}
          {shown.map((o, i) => (
            <li
              key={o.value || "__empty"}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={o.value === value}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(o);
              }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-start gap-2 rounded-md px-2.5 py-1.5 ${i === active ? "bg-accent-soft" : ""}`}
            >
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{o.label}</span>
                {o.sub && <span className="block text-sm leading-snug text-muted">{o.sub}</span>}
              </span>
              {o.value === value && <Check className="mt-1 h-4 w-4 shrink-0 text-accent" aria-hidden />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

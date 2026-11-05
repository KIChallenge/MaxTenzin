"use client";
import { useEffect, useRef, useState, useTransition } from "react";
import { Check, ChevronDown } from "lucide-react";
import { useRouter } from "next/navigation";
import { setLargeText, setPlain, setSubject } from "@/app/actions";

type SubjectOption = { id: string; name: string; sub: string; initials: string };

/** "Für wen handle ich?" – a popover menu (menuitemradio), only rendered when the actor may represent someone. */
export function SubjectSwitcher({ current, options }: { current: string; options: SubjectOption[] }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [pending, start] = useTransition();
  const router = useRouter();
  const root = useRef<HTMLDivElement>(null);
  const items = useRef<(HTMLButtonElement | null)[]>([]);
  const cur = options.find((o) => o.id === current) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const i = Math.max(0, options.findIndex((o) => o.id === current));
    setActive(i);
    requestAnimationFrame(() => items.current[i]?.focus());
    const close = (e: MouseEvent) => !root.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open, current, options]);

  function choose(id: string) {
    setOpen(false);
    if (id === current) return;
    start(async () => {
      await setSubject(id);
      router.refresh();
    });
  }
  function onKey(e: React.KeyboardEvent) {
    if (e.key === "Escape") return setOpen(false);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const n = (active + (e.key === "ArrowDown" ? 1 : -1) + options.length) % options.length;
      setActive(n);
      items.current[n]?.focus();
    }
  }

  return (
    <div ref={root} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Handeln für: ${cur.name}`}
        disabled={pending}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full border border-line bg-surface py-0.5 pr-2.5 pl-0.5 hover:bg-neutral-soft disabled:opacity-60"
      >
        <Initials text={cur.initials} self={cur.id === options[0]?.id} />
        <span className="max-w-40 truncate font-semibold">{cur.id === options[0]?.id ? "Ich" : cur.name}</span>
        <ChevronDown className={`h-4 w-4 text-muted transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
      </button>
      {open && (
        <div
          role="menu"
          aria-label="Handeln für"
          onKeyDown={onKey}
          className="absolute right-0 z-50 mt-2 w-72 origin-top-right rounded-xl border border-line bg-surface/95 p-1.5 shadow-xl backdrop-blur-xl"
        >
          <p className="px-2.5 pt-1.5 pb-1 text-xs font-semibold text-muted">Handeln für</p>
          {options.map((o, i) => (
            <button
              key={o.id}
              ref={(el) => {
                items.current[i] = el;
              }}
              type="button"
              role="menuitemradio"
              aria-checked={o.id === current}
              tabIndex={i === active ? 0 : -1}
              onClick={() => choose(o.id)}
              className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left hover:bg-neutral-soft focus:bg-neutral-soft focus:outline-none"
            >
              <Initials text={o.initials} self={i === 0} />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold">{o.name}</span>
                <span className="block truncate text-sm text-muted">{o.sub}</span>
              </span>
              {o.id === current && <Check className="h-4 w-4 text-accent" aria-hidden />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Initials({ text, self }: { text: string; self: boolean }) {
  return (
    <span
      aria-hidden
      className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-semibold ${
        self ? "bg-accent text-white" : "bg-info-soft text-info"
      }`}
    >
      {text}
    </span>
  );
}

/** A settings row with an iOS-style switch. */
function SettingSwitch({ on, label, hint, onToggle }: { on: boolean; label: string; hint: string; onToggle: (next: boolean) => Promise<void> }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  return (
    <div className="flex items-center gap-4 px-4 py-3">
      <div className="flex-1">
        <p className="font-semibold">{label}</p>
        <p className="text-sm text-muted">{hint}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={label}
        disabled={pending}
        onClick={() =>
          start(async () => {
            await onToggle(!on);
            router.refresh();
          })
        }
        className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${on ? "bg-accent" : "bg-muted/35"}`}
      >
        <span className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-all ${on ? "left-[1.375rem]" : "left-0.5"}`} />
      </button>
    </div>
  );
}

export function PlainToggle({ on }: { on: boolean }) {
  return <SettingSwitch on={on} label="Einfache Sprache" hint="Kürzere Sätze und einfache Erklärungen – auch in den Antworten von Lotsi." onToggle={setPlain} />;
}

export function LargeTextToggle({ on }: { on: boolean }) {
  return <SettingSwitch on={on} label="Größere Schrift" hint="Alle Texte etwas größer. Sie können auch im Browser zoomen (⌘ +)." onToggle={setLargeText} />;
}

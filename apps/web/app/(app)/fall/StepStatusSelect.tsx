"use client";
// Status of a case step as a pill menu (same pattern as the person switch): the button *is* the status.
import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Check, ChevronDown } from "lucide-react";
import { bff } from "@/lib/client";
import type { Case, StepStatus } from "@/lib/types";

const STATUS: Record<StepStatus, { label: string; hint: string; pill: string; dot: string }> = {
  open: { label: "Offen", hint: "noch nicht begonnen", pill: "border-neutral/30 bg-neutral-soft text-neutral", dot: "bg-neutral/60" },
  in_progress: { label: "In Arbeit", hint: "wird gerade erledigt", pill: "border-info/30 bg-info-soft text-info", dot: "bg-info" },
  done: { label: "Erledigt", hint: "abgeschlossen", pill: "border-ok/30 bg-ok-soft text-ok", dot: "bg-ok" },
  blocked: { label: "Blockiert", hint: "wartet auf jemand anderen", pill: "border-danger/30 bg-danger-soft text-danger", dot: "bg-danger" },
};
const ORDER: StepStatus[] = ["open", "in_progress", "done", "blocked"];

export function StepStatusSelect({ caseId, stepId, status, label }: { caseId: string; stepId: string; status: StepStatus; label: string }) {
  const [value, setValue] = useState(status);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const router = useRouter();
  const root = useRef<HTMLDivElement>(null);
  const items = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => setValue(status), [status]);
  useEffect(() => {
    if (!open) return;
    const i = ORDER.indexOf(value);
    setActive(i);
    requestAnimationFrame(() => items.current[i]?.focus());
    const close = (e: MouseEvent) => !root.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open, value]);

  function choose(next: StepStatus) {
    setOpen(false);
    if (next === value) return;
    const prev = value;
    setValue(next); // optimistic
    start(async () => {
      const r = await bff<Case>(`/api/cases/${caseId}/steps/${stepId}`, { method: "PATCH", body: { status: next } });
      if (!r.ok) {
        setValue(prev);
        setErr("Konnte nicht gespeichert werden.");
      } else {
        setErr(null);
        router.refresh();
      }
    });
  }

  const s = STATUS[value];
  return (
    <div ref={root} className="relative inline-flex flex-col items-end">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Status von „${label}“: ${s.label}. Ändern`}
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex items-center gap-1.5 rounded-full border py-0.5 pr-1.5 pl-2.5 text-sm font-semibold transition-opacity ${s.pill} ${pending ? "opacity-60" : ""}`}
      >
        <span aria-hidden className={`h-2 w-2 rounded-full ${s.dot}`} />
        {s.label}
        <ChevronDown className={`h-3.5 w-3.5 opacity-70 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />
      </button>
      {open && (
        <div
          role="menu"
          aria-label={`Status von „${label}“`}
          onKeyDown={(e) => {
            if (e.key === "Escape") return setOpen(false);
            if (e.key === "ArrowDown" || e.key === "ArrowUp") {
              e.preventDefault();
              const n = (active + (e.key === "ArrowDown" ? 1 : -1) + ORDER.length) % ORDER.length;
              setActive(n);
              items.current[n]?.focus();
            }
          }}
          className="absolute top-full right-0 z-30 mt-1.5 w-60 rounded-xl border border-line bg-surface/95 p-1 shadow-xl backdrop-blur-xl"
        >
          {ORDER.map((k, i) => (
            <button
              key={k}
              ref={(el) => {
                items.current[i] = el;
              }}
              type="button"
              role="menuitemradio"
              aria-checked={k === value}
              tabIndex={i === active ? 0 : -1}
              onClick={() => choose(k)}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left hover:bg-neutral-soft focus:bg-neutral-soft focus:outline-none"
            >
              <span aria-hidden className={`h-2.5 w-2.5 shrink-0 rounded-full ${STATUS[k].dot}`} />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-semibold">{STATUS[k].label}</span>
                <span className="block text-xs text-muted">{STATUS[k].hint}</span>
              </span>
              {k === value && <Check className="h-4 w-4 text-accent" aria-hidden />}
            </button>
          ))}
        </div>
      )}
      {err && (
        <span role="alert" className="mt-1 text-xs text-danger">
          {err}
        </span>
      )}
    </div>
  );
}

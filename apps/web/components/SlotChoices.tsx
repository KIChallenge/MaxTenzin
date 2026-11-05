"use client";
// Free slots Lotsi just found, as buttons. Same search (arguments from the tool trace) → same result list;
// a click sends the explicit choice back to Lotsi, who books it (booking only after an explicit choice).
import { useEffect, useState } from "react";
import { CalendarCheck } from "lucide-react";
import { bff } from "@/lib/client";
import type { Slot } from "@/lib/care";

const day = (iso: string) => new Date(iso).toLocaleDateString("de-AT", { weekday: "short", day: "numeric", month: "numeric" });
const time = (iso: string) => new Date(iso).toLocaleTimeString("de-AT", { hour: "2-digit", minute: "2-digit" });

export function SlotChoices({ args, onChoose, disabled }: { args: Record<string, unknown>; onChoose: (text: string) => void; disabled: boolean }) {
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const key = JSON.stringify(args);
  useEffect(() => {
    let alive = true;
    bff<Slot[]>("/api/appointments/slots/search", { method: "POST", body: { limit: 5, ...JSON.parse(key) } }).then((r) => alive && setSlots(r.ok ? r.data : []));
    return () => {
      alive = false;
    };
  }, [key]);
  if (!slots?.length) return null;
  const oneProvider = slots.every((s) => s.provider.id === slots[0].provider.id);
  return (
    <div className="rounded-lg border border-line bg-surface p-2">
      <p className="mb-1.5 px-1 text-xs font-semibold text-muted">
        Termin wählen{oneProvider ? ` · ${slots[0].provider.name}` : ""}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {slots.map((s) => (
          <button
            key={s.id}
            type="button"
            disabled={disabled}
            onClick={() =>
              onChoose(
                `Bitte den Termin am ${new Date(s.start).toLocaleDateString("de-AT", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" })} um ${time(s.start)} bei ${s.provider.name} buchen.`,
              )
            }
            className="inline-flex flex-col items-start rounded-md border border-line px-2.5 py-1 text-left text-sm hover:border-accent hover:bg-accent-soft disabled:opacity-50"
          >
            <span className="inline-flex items-center gap-1 font-semibold tabular-nums">
              <CalendarCheck className="h-3.5 w-3.5 text-accent" aria-hidden /> {day(s.start)}, {time(s.start)}
            </span>
            {!oneProvider && <span className="max-w-48 truncate text-xs text-muted">{s.provider.name}</span>}
          </button>
        ))}
      </div>
      <p className="mt-1.5 px-1 text-xs text-muted">Demo-Termine – gebucht wird erst nach Ihrer Auswahl.</p>
    </div>
  );
}

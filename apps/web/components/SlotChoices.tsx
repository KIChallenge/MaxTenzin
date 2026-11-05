"use client";
// Slots Lotsi offered (ChatAction kind "choose_slot", same order as its numbered list) as buttons.
// A click sends the explicit choice back to Lotsi, who books exactly that slot.
import { CalendarCheck } from "lucide-react";
import type { ChatAction } from "@/lib/types";

export function SlotChoices({ actions, onChoose, disabled }: { actions: ChatAction[]; onChoose: (text: string) => void; disabled: boolean }) {
  if (!actions.length) return null;
  // "Fr. 6.11., 08:40 · Ordination Dr. Muster (Demo)" → time part + provider part
  const parts = actions.map((a) => {
    const [when, ...rest] = a.label_de.split(" · ");
    return { a, when, provider: rest.join(" · ") };
  });
  const oneProvider = parts.every((p) => p.provider === parts[0].provider);
  return (
    <div className="rounded-lg border border-line bg-surface p-2">
      <p className="mb-1.5 px-1 text-xs font-semibold text-muted">
        Termin wählen{oneProvider && parts[0].provider ? ` · ${parts[0].provider}` : ""}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {parts.map(({ a, when, provider }, i) => (
          <button
            key={a.url}
            type="button"
            disabled={disabled}
            onClick={() => onChoose(`Bitte Termin ${i + 1} buchen: ${a.label_de}.`)}
            className="inline-flex flex-col items-start rounded-md border border-line px-2.5 py-1 text-left text-sm hover:border-accent hover:bg-accent-soft disabled:opacity-50"
          >
            <span className="inline-flex items-center gap-1 font-semibold tabular-nums">
              <CalendarCheck className="h-3.5 w-3.5 text-accent" aria-hidden /> {when}
            </span>
            {!oneProvider && provider && <span className="max-w-48 truncate text-xs text-muted">{provider}</span>}
          </button>
        ))}
      </div>
      <p className="mt-1.5 px-1 text-xs text-muted">Demo-Termine – gebucht wird erst nach Ihrer Auswahl.</p>
    </div>
  );
}

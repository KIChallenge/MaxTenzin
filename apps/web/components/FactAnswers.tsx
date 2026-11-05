"use client";
import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { saveFact } from "@/app/actions";
import { type FactValue, factLabel, fmtFact } from "@/lib/facts";

/** Answers already given – visible, and removable, so nobody wonders why a result changed. */
export function FactAnswers({ facts, name }: { facts: Record<string, FactValue>; name: string }) {
  const [pending, start] = useTransition();
  const router = useRouter();
  const entries = Object.entries(facts);
  if (!entries.length) return null;
  return (
    <div className="mb-4 rounded-lg border border-line bg-surface px-3 py-2 text-sm" aria-busy={pending}>
      <span className="font-semibold">Ihre Angaben zu {name}: </span>
      <span className="text-muted">fließen in die Prüfung ein.</span>
      <ul className="mt-1.5 flex flex-wrap gap-1.5">
        {entries.map(([k, v]) => (
          <li key={k} className="inline-flex items-center gap-1 rounded-full border border-line bg-paper py-0.5 pr-1 pl-2.5">
            <span className="text-muted">{factLabel(k).replace(/\?$/, "")}:</span> <strong>{fmtFact(k, v)}</strong>
            <button
              type="button"
              aria-label={`Angabe „${factLabel(k)}“ entfernen`}
              className="rounded-full p-0.5 hover:bg-neutral-soft"
              onClick={() =>
                start(async () => {
                  await saveFact(k, null);
                  router.refresh();
                })
              }
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

"use client";
// One open question of the eligibility check, answered right here. Saving re-runs the check (server refresh).
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Check, LoaderCircle, MessageCircleQuestion } from "lucide-react";
import { saveFact } from "@/app/actions";
import { FACTS, factLabel } from "@/lib/facts";
import { askLotsi } from "./OpenChatButton";

export function FactQuestion({ factKey, benefitName }: { factKey: string; benefitName: string }) {
  const def = FACTS[factKey];
  const [draft, setDraft] = useState("");
  const [pending, start] = useTransition();
  const router = useRouter();
  const save = (v: string | number | boolean) =>
    start(async () => {
      await saveFact(factKey, v);
      router.refresh();
    });

  const input = def?.input ?? { kind: "text" as const };
  return (
    <li className="px-3 py-2.5">
      <p className="font-semibold">{factLabel(factKey)}</p>
      {def?.hint && <p className="text-sm text-muted">{def.hint}</p>}
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        {input.kind === "bool" && (
          <>
            <button type="button" className="btn-secondary px-3 py-1 text-sm" disabled={pending} onClick={() => save(true)}>
              Ja
            </button>
            <button type="button" className="btn-secondary px-3 py-1 text-sm" disabled={pending} onClick={() => save(false)}>
              Nein
            </button>
          </>
        )}
        {input.kind === "choice" &&
          input.options.map(([k, l]) => (
            <button key={k} type="button" className="btn-secondary px-3 py-1 text-sm" disabled={pending} onClick={() => save(k)}>
              {l}
            </button>
          ))}
        {(input.kind === "number" || input.kind === "text") && (
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (!draft.trim()) return;
              save(input.kind === "number" ? Number(draft.replace(",", ".")) : draft.trim());
            }}
          >
            <input
              aria-label={factLabel(factKey)}
              className="input w-36 py-1"
              inputMode={input.kind === "number" ? "decimal" : undefined}
              placeholder={input.kind === "text" ? input.placeholder : undefined}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            {input.kind === "number" && input.unit && <span className="text-sm text-muted">{input.unit}</span>}
            <button className="btn-primary px-3 py-1 text-sm" disabled={pending || !draft.trim()}>
              <Check className="h-4 w-4" aria-hidden /> Übernehmen
            </button>
          </form>
        )}
        {pending && <LoaderCircle className="h-4 w-4 animate-spin text-accent" aria-label="Wird neu geprüft" />}
        <button
          type="button"
          className="ml-auto inline-flex items-center gap-1 text-sm text-muted hover:text-accent"
          onClick={() =>
            askLotsi(
              `Ich prüfe „${benefitName}“. Offene Frage: „${factLabel(factKey)}“. Wie finde ich das heraus, und wo steht das vielleicht schon in den Unterlagen?`,
            )
          }
        >
          <MessageCircleQuestion className="h-4 w-4" aria-hidden /> Weiß ich nicht – Lotsi fragen
        </button>
      </div>
    </li>
  );
}

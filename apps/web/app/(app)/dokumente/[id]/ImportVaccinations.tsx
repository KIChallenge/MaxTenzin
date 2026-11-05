"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { bff } from "@/lib/client";
import type { PreventionOverview } from "@/lib/types";

/** e-Impfpass → Vorsorge: imports the documented vaccinations (deterministic, no interpretation). */
export function ImportVaccinations({ documentId, subjectName }: { documentId: string; subjectName: string }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();
  return (
    <div className="card mt-6 flex flex-wrap items-center gap-4 border-accent/30 bg-accent-soft">
      <div className="flex-1">
        <p className="text-lg font-bold">Impfungen in „Vorsorge“ übernehmen</p>
        <p className="text-muted">Wir übernehmen nur die dokumentierten Einträge und vergleichen sie mit dem Österreichischen Impfplan.</p>
        {err && (
          <p role="alert" className="mt-2 text-danger">
            {err}
          </p>
        )}
      </div>
      <button
        type="button"
        className="btn-primary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          const r = await bff<PreventionOverview>(`/api/prevention/import/${documentId}`, { method: "POST" });
          setBusy(false);
          if (!r.ok) return setErr(r.status === 403 ? `Dafür hat ${subjectName} keine Berechtigung erteilt. ${r.detail}` : r.detail);
          router.push("/vorsorge");
        }}
      >
        {busy ? "Wird übernommen …" : "In Vorsorge übernehmen →"}
      </button>
    </div>
  );
}

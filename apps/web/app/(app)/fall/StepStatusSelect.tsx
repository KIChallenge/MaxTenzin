"use client";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { bff } from "@/lib/client";
import { STEP_STATUS } from "@/lib/labels";
import type { Case, StepStatus } from "@/lib/types";

export function StepStatusSelect({ caseId, stepId, status, label }: { caseId: string; stepId: string; status: StepStatus; label: string }) {
  const [value, setValue] = useState(status);
  const [err, setErr] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const router = useRouter();
  return (
    <span className="inline-flex flex-col items-end">
      <select
        aria-label={`Status von „${label}"`}
        className="rounded-lg border border-line bg-surface px-2 py-1 font-bold"
        value={value}
        disabled={pending}
        onChange={(e) => {
          const next = e.target.value as StepStatus;
          setValue(next);
          start(async () => {
            const r = await bff<Case>(`/api/cases/${caseId}/steps/${stepId}`, { method: "PATCH", body: { status: next } });
            if (!r.ok) {
              setErr(r.detail);
              setValue(status);
            } else {
              setErr(null);
              router.refresh();
            }
          });
        }}
      >
        {(Object.keys(STEP_STATUS) as StepStatus[]).map((s) => (
          <option key={s} value={s}>
            {STEP_STATUS[s].label}
          </option>
        ))}
      </select>
      {err && <span role="alert" className="mt-1 text-sm text-danger">{err}</span>}
    </span>
  );
}

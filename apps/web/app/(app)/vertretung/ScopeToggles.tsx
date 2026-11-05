"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { bff } from "@/lib/client";
import { ALL_SCOPES, SCOPE_LABELS } from "@/lib/labels";
import type { Delegation, Scope } from "@/lib/types";

export function ScopeToggles({ delegation, editable }: { delegation: Delegation; editable: boolean }) {
  const [scopes, setScopes] = useState<Scope[]>(delegation.scopes);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function toggle(s: Scope) {
    const next = scopes.includes(s) ? scopes.filter((x) => x !== s) : [...scopes, s];
    setBusy(true);
    const r = await bff<Delegation>(`/api/identity/delegations/${delegation.id}/scopes`, { method: "PUT", body: next });
    setBusy(false);
    if (!r.ok) return setErr(r.detail);
    setErr(null);
    setScopes(r.data.scopes);
    router.refresh();
  }

  return (
    <div>
      <ul className="mt-3 space-y-2">
        {ALL_SCOPES.map((s) => {
          const on = scopes.includes(s);
          return (
            <li key={s}>
              <label className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${on ? "border-ok/40 bg-ok-soft" : "border-line"}`}>
                <input type="checkbox" className="h-5 w-5 accent-accent" checked={on} disabled={!editable || busy} onChange={() => toggle(s)} />
                <span className="font-bold">{SCOPE_LABELS[s]}</span>
                <span className="ml-auto text-sm">{on ? "erlaubt" : "nicht erlaubt"}</span>
              </label>
            </li>
          );
        })}
      </ul>
      {err && <p role="alert" className="mt-2 text-danger">{err}</p>}
    </div>
  );
}

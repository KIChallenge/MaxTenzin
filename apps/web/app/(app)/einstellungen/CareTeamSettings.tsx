"use client";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Accessibility } from "lucide-react";
import { bff } from "@/lib/client";
import type { CareTeam, Provider } from "@/lib/care";

/** Change the Hausärztin/Hausarzt (PUT /api/identity/care-team). */
export function CareTeamSettings({ team, gps }: { team: CareTeam; gps: Provider[] }) {
  const current = team.members.find((m) => m.role === "hausarzt");
  const [choice, setChoice] = useState(current?.provider_id ?? "");
  const [msg, setMsg] = useState<string | null>(null);
  const [pending, start] = useTransition();
  const router = useRouter();
  const options = gps.some((g) => g.id === current?.provider_id) || !current ? gps : [{ id: current.provider_id, name: current.name, zip: "", city: "", accessible: false } as Provider, ...gps];

  return (
    <div className="divide-y divide-line rounded-xl border border-line bg-surface">
      {team.members.map((m) => (
        <div key={m.role} className="px-4 py-3">
          <p className="text-sm text-muted">{m.role_de}</p>
          <p className="font-semibold">{m.name}</p>
          <p className="text-sm text-muted">{m.address}</p>
        </div>
      ))}
      <form
        className="flex flex-wrap items-end gap-3 px-4 py-3"
        onSubmit={(e) => {
          e.preventDefault();
          setMsg(null);
          start(async () => {
            const r = await bff("/api/identity/care-team", { method: "PUT", body: { role: "hausarzt", provider_id: choice } });
            setMsg(r.ok ? "Gespeichert." : r.detail);
            if (r.ok) router.refresh();
          });
        }}
      >
        <label className="flex min-w-64 flex-1 flex-col gap-1">
          <span className="font-semibold">Hausärztin / Hausarzt ändern</span>
          <select className="input" value={choice} onChange={(e) => setChoice(e.target.value)}>
            {options.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
                {g.zip ? ` – ${g.zip} ${g.city}` : ""}
                {g.accessible ? " · barrierefrei" : ""}
              </option>
            ))}
          </select>
        </label>
        <button className="btn-secondary" disabled={pending || choice === current?.provider_id}>
          Speichern
        </button>
        {msg && <p className="w-full text-sm text-muted">{msg}</p>}
        <p className="flex w-full items-center gap-1.5 text-sm text-muted">
          <Accessibility className="h-4 w-4" aria-hidden /> {team.notice_de}
        </p>
      </form>
    </div>
  );
}

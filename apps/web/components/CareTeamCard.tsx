import Link from "next/link";
import { CalendarPlus, Phone } from "lucide-react";
import type { ApiResult } from "@/lib/types";
import type { CareTeam } from "@/lib/care";
import { SourceChip } from "./SourceChip";

/** "Ihr Behandlungsteam" on the overview: Hausärztin first, each with a direct way to book. */
export function CareTeamCard({ team, firstName, forOther }: { team: ApiResult<CareTeam>; firstName: string; forOther: boolean }) {
  if (!team.ok) return null; // missing scope or service down: the overview stays usable without it
  const members = [...team.data.members].sort((a, b) => (a.role === "hausarzt" ? -1 : b.role === "hausarzt" ? 1 : 0));
  return (
    <section aria-labelledby="team-h" className="mb-6">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 id="team-h" className="text-lg font-semibold">
          {forOther ? `Behandlungsteam von ${firstName}` : "Ihr Behandlungsteam"}
        </h2>
        <Link href="/einstellungen#behandlungsteam" className="text-sm text-muted hover:text-ink">
          Ändern
        </Link>
      </div>
      {members.length === 0 ? (
        <p className="card text-sm text-muted">Noch keine Hausärztin bzw. kein Hausarzt hinterlegt.</p>
      ) : (
        <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
          {members.map((m) => (
            <li key={m.role + m.provider_id} className="px-4 py-2.5">
              <p className="text-xs font-semibold text-muted">{m.role_de}</p>
              <p className="font-semibold">{m.name}</p>
              <p className="text-sm text-muted">{m.address}</p>
              <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                {m.phone && (
                  <a href={`tel:${m.phone.replace(/[^\d+]/g, "")}`} className="inline-flex items-center gap-1 text-accent hover:underline">
                    <Phone className="h-3.5 w-3.5" aria-hidden />
                    {m.phone}
                  </a>
                )}
                {m.provider_id && (
                  <Link href={`/termine?provider=${encodeURIComponent(m.provider_id)}`} className="inline-flex items-center gap-1 font-semibold text-accent hover:underline">
                    <CalendarPlus className="h-3.5 w-3.5" aria-hidden />
                    Termin buchen
                  </Link>
                )}
                {m.source && <SourceChip source={m.source} />}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

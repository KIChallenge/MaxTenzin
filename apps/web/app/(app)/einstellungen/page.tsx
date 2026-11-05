import { cookies } from "next/headers";
import { ApiError } from "@/components/ApiError";
import { LargeTextToggle, PlainToggle } from "@/components/HeaderControls";
import { PageTitle } from "@/components/PageTitle";
import { api, isPlain } from "@/lib/api";
import { fmtDate, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import { COOKIE_TEXT } from "@/lib/session";
import type { Delegation, Person } from "@/lib/types";
import { ScopeToggles } from "./ScopeToggles";
import { CareTeamSettings } from "./CareTeamSettings";
import { PreferencesForm } from "./PreferencesForm";
import type { CareTeam, Preferences, Provider } from "@/lib/care";

export default async function SettingsPage() {
  const [me, dels, personas, plain, jar, team, prefs] = await Promise.all([
    getMe(),
    api<Delegation[]>("/api/identity/delegations"),
    api<Person[]>("/api/identity/personas"),
    isPlain(),
    cookies(),
    api<CareTeam>("/api/identity/care-team"),
    api<Preferences>("/api/identity/preferences"),
  ]);
  const zip = me.ok ? me.data.subject.address.zip : "";
  const providers = team.ok ? await api<Provider[]>(`/api/appointments/providers?zip=${encodeURIComponent(zip)}`) : null;
  const gps = providers?.ok ? providers.data.filter((p) => p.kind === "gp") : [];
  if (!me.ok) return <ApiError status={me.status} detail={me.detail} />;
  const large = jar.get(COOKIE_TEXT)?.value === "large";
  const names = new Map((personas.ok ? personas.data : []).map((p) => [p.id, fullName(p)]));
  const { actor, subject } = me.data;
  const forOther = actor.id !== subject.id;
  const list: Delegation[] = [...(dels.ok ? dels.data : []), ...(me.data.delegations ?? [])].filter(
    (d, i, all) => all.findIndex((x) => x.id === d.id) === i,
  );

  return (
    <div className="max-w-3xl">
      <PageTitle title="Einstellungen" />

      <section aria-labelledby="darstellung-h" className="mb-8">
        <h2 id="darstellung-h" className="mb-2 text-lg font-semibold">
          Darstellung
        </h2>
        <div className="divide-y divide-line rounded-xl border border-line bg-surface">
          <PlainToggle on={plain} />
          <LargeTextToggle on={large} />
        </div>
      </section>

      {prefs.ok && <PreferencesForm initial={prefs.data} actorFirstName={actor.first_name} />}

      {team.ok && (
        <section id="behandlungsteam" aria-labelledby="team-h" className="mb-8 scroll-mt-28">
          <h2 id="team-h" className="mb-2 text-lg font-semibold">
            Behandlungsteam{forOther ? ` von ${subject.first_name}` : ""}
          </h2>
          <CareTeamSettings team={team.data} gps={gps} />
        </section>
      )}

      <section id="vollmachten" aria-labelledby="vollmachten-h" className="scroll-mt-28">
        <h2 id="vollmachten-h" className="mb-1 text-lg font-semibold">
          Vollmachten
        </h2>
        <p className="mb-3 text-muted">
          Nur die vertretene Person entscheidet, was ihre Vertretung – und damit auch Lotsi – tun darf.
        </p>
        <div role="note" className="mb-4 rounded-lg border-l-4 border-info bg-info-soft px-4 py-3 text-sm">
          <strong className="font-semibold">Demo:</strong> Im Echtbetrieb werden Vollmachten und Vertretungen über ID Austria
          erteilt und verwaltet – nicht in dieser Anwendung. Hier lassen sich die Berechtigungen nur zu Demonstrationszwecken
          ändern.
        </div>
        {!dels.ok && <ApiError status={dels.status} detail={dels.detail} />}
        {list.length === 0 && dels.ok && <p className="card text-muted">Keine Vollmachten vorhanden.</p>}
        <div className="space-y-4">
          {list.map((d) => {
            const editable = actor.id === d.grantor_id;
            return (
              <article key={d.id} className="card">
                <h3 className="font-semibold">
                  {names.get(d.grantor_id) ?? d.grantor_id} → {names.get(d.grantee_id) ?? d.grantee_id}
                </h3>
                <p className="text-sm text-muted">
                  {d.relation && `${d.relation}, `}
                  {d.valid_until ? `gültig bis ${fmtDate(d.valid_until)}` : "unbefristet"}
                </p>
                {d.consent_note && <p className="mt-2 text-sm">{d.consent_note}</p>}
                <ScopeToggles delegation={d} editable={editable} />
                {!editable && (
                  <p className="mt-3 text-sm text-muted">
                    Nur {names.get(d.grantor_id) ?? "die vertretene Person"} kann diese Berechtigungen ändern
                    {forOther ? " (Demo: als diese Person anmelden)." : "."}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { fmtDate, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { Delegation, Person } from "@/lib/types";
import { ScopeToggles } from "./ScopeToggles";

export default async function DelegationPage() {
  const [me, dels, personas] = await Promise.all([getMe(), api<Delegation[]>("/api/identity/delegations"), api<Person[]>("/api/identity/personas")]);
  if (!me.ok) return <ApiError status={me.status} detail={me.detail} />;
  const names = new Map((personas.ok ? personas.data : []).map((p) => [p.id, fullName(p)]));
  const { actor, subject } = me.data;
  const forOther = actor.id !== subject.id;
  // Delegations the actor holds (from the login session) + those the subject granted.
  const list: Delegation[] = [...(dels.ok ? dels.data : []), ...(me.data.delegations ?? [])].filter(
    (d, i, all) => all.findIndex((x) => x.id === d.id) === i,
  );
  return (
    <>
      <PageTitle eyebrow="Vertretung" title="Vertretung & Berechtigungen">
        Nur die vertretene Person entscheidet, was ihre Vertretung – und damit auch der KI-Lotse – tun darf.
      </PageTitle>
      {!dels.ok && <ApiError status={dels.status} detail={dels.detail} />}
      {list.length === 0 && dels.ok && <p className="card text-muted">Keine Vollmachten vorhanden.</p>}
      <div className="grid gap-6 md:grid-cols-2">
        {list.map((d) => {
          const editable = actor.id === d.grantor_id;
          return (
            <section key={d.id} className="card">
              <p className="eyebrow">Vollmacht</p>
              <h2 className="text-xl font-bold">
                {names.get(d.grantor_id) ?? d.grantor_id} → {names.get(d.grantee_id) ?? d.grantee_id}
              </h2>
              <p className="text-muted">
                {d.relation && `${d.relation} · `}
                {d.valid_until ? `gültig bis ${fmtDate(d.valid_until)}` : "unbefristet"}
              </p>
              {d.consent_note && <p className="mt-2">{d.consent_note}</p>}
              <ScopeToggles delegation={d} editable={editable} />
              {!editable && (
                <p className="mt-3 rounded-lg bg-info-soft p-3">
                  Nur {names.get(d.grantor_id) ?? "die vertretene Person"} kann diese Berechtigungen ändern.
                  {forOther && " (Demo: als diese Person anmelden.)"}
                </p>
              )}
            </section>
          );
        })}
      </div>
    </>
  );
}

import { Lebenslage } from "@/components/Lebenslage";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { SituationOverview } from "@/lib/situation";

export default async function LebenslagePage() {
  const [me, situation] = await Promise.all([getMe(), api<SituationOverview>("/api/situation")]);
  const subject = me.ok ? me.data.subject : null;
  return (
    <div className="max-w-4xl">
      <PageTitle eyebrow="Lebenslage" title={`Wo ${subject?.first_name ?? ""} gerade steht`}>
        Krankenhaus, Reha, Therapie, zu Hause mit Unterstützung – daraus ergeben sich Fristen, passende Leistungen und
        Angaben für Anträge. Vorschläge aus Dokumenten gelten erst nach Ihrer Zustimmung.
      </PageTitle>
      <Lebenslage
        {...(situation.ok ? { ok: true as const, data: situation.data } : { ok: false as const, status: situation.status, detail: situation.detail })}
        subjectName={subject ? fullName(subject) : ""}
        firstName={subject?.first_name ?? ""}
      />
    </div>
  );
}

import { Mail, Phone } from "lucide-react";
import { ApiError } from "@/components/ApiError";
import { FormPicker } from "@/components/FormPicker";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { getMe } from "@/lib/me";
import type { Office } from "@/lib/types";

// Topic ids of the directory → plain German (unknown ids are shown as they come, prettified).
const TOPIC_LABELS: Record<string, string> = {
  pflegegeld: "Pflegegeld",
  pflegeberatung: "Pflegeberatung",
  pflege: "Pflege allgemein",
  mobile_pflege: "Mobile Pflege",
  fsw_mobile_pflege: "Mobile Pflege (FSW)",
  hauskrankenpflege: "Medizinische Hauskrankenpflege",
  reha: "Rehabilitation",
  reha_onko: "Onkologische Rehabilitation",
  krankentransport: "Krankentransport",
  fahrtkostenzuschuss: "Fahrtkostenzuschuss",
  rezeptgebuehr: "Rezeptgebühr",
  rezeptgebuehrenbefreiung: "Rezeptgebührenbefreiung",
  rezeptgebuehrenobergrenze: "Rezeptgebühren-Obergrenze",
  heilbehelfe_hilfsmittel: "Heilbehelfe und Hilfsmittel",
  unterstuetzungsfonds: "Unterstützungsfonds",
  vorsorgeuntersuchung: "Vorsorgeuntersuchung",
  gesundheitszentrum: "Gesundheitszentrum",
  gesundheitsberatung: "Gesundheitsberatung",
  oegk_kundenservice: "ÖGK-Kundenservice",
  kinderbetreuungsgeld: "Kinderbetreuungsgeld",
  eltern_kind_pass: "Eltern-Kind-Pass",
  familie: "Familie",
  pension: "Pension",
  selbstversicherung_pflege: "Selbstversicherung für pflegende Angehörige",
  akut: "Akut / Notfall",
};
const topicLabel = (t: string) => TOPIC_LABELS[t] ?? t.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export default async function OfficesPage({ searchParams }: { searchParams: Promise<{ topic?: string; zip?: string }> }) {
  const sp = await searchParams;
  const me = await getMe();
  const topic = sp.topic ?? "pflegegeld";
  const zip = sp.zip ?? (me.ok ? me.data.subject.address.zip : "");
  const r = await api<Office[]>(`/api/directory/offices?topic=${encodeURIComponent(topic)}&zip=${encodeURIComponent(zip)}`);
  const topics = [...new Set([...Object.keys(TOPIC_LABELS), topic])].sort((a, b) => topicLabel(a).localeCompare(topicLabel(b), "de"));
  return (
    <>
      <PageTitle title="Wo reiche ich das ein?">
        Zuständige Stelle nach Thema und Postleitzahl.
      </PageTitle>
      <form className="card mb-6 flex flex-wrap items-end gap-4">
        <FormPicker name="topic" label="Thema" defaultValue={topic} className="min-w-72" options={topics.map((t) => ({ value: t, label: topicLabel(t), search: t }))} />
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Postleitzahl</span>
          <input name="zip" defaultValue={zip} className="input w-32" inputMode="numeric" />
        </label>
        <button className="btn-primary">Suchen</button>
      </form>
      {!r.ok ? (
        <ApiError status={r.status} detail={r.detail} />
      ) : r.data.length === 0 ? (
        <p className="card text-muted">Keine Stelle gefunden.</p>
      ) : (
        <ul className="grid gap-4 md:grid-cols-2">
          {r.data.map((o) => (
            <li key={o.id} className="card">
              <p className="eyebrow">{o.provider}</p>
              <h2 className="text-lg font-semibold">{o.name}</h2>
              <address className="mt-1 not-italic">
                {o.address}, {o.zip} {o.city}
              </address>
              <p className="mt-1">
                {o.phone && <span className="mr-4 inline-flex items-center gap-1.5"><Phone className="h-4 w-4 text-muted" aria-hidden /><a className="link" href={`tel:${o.phone.replace(/\s/g, "")}`}>{o.phone}</a></span>}
                {o.email && <span className="inline-flex items-center gap-1.5"><Mail className="h-4 w-4 text-muted" aria-hidden /><a className="link" href={`mailto:${o.email}`}>{o.email}</a></span>}
              </p>
              {o.web && <a className="link" href={o.web}>{o.web}</a>}
              <p className="mt-2"><SourceChip source={o.source} /></p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

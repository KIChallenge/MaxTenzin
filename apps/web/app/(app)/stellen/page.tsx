import { Mail, Phone } from "lucide-react";
import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { getMe } from "@/lib/me";
import type { Office } from "@/lib/types";

const TOPICS = [
  ["pflegegeld", "Pflegegeld"],
  ["reha", "Rehabilitation"],
  ["mobile_pflege", "Mobile Pflege"],
  ["krankentransport", "Krankentransport"],
  ["rezeptgebuehr", "Rezeptgebühr"],
  ["vorsorge", "Vorsorge"],
] as const;

export default async function OfficesPage({ searchParams }: { searchParams: Promise<{ topic?: string; zip?: string }> }) {
  const sp = await searchParams;
  const me = await getMe();
  const topic = sp.topic ?? "pflegegeld";
  const zip = sp.zip ?? (me.ok ? me.data.subject.address.zip : "");
  const r = await api<Office[]>(`/api/directory/offices?topic=${encodeURIComponent(topic)}&zip=${encodeURIComponent(zip)}`);
  return (
    <>
      <PageTitle eyebrow="Zuständige Stellen" title="Wo reiche ich das ein?">
        Zuständige Stelle nach Thema und Postleitzahl.
      </PageTitle>
      <form className="card mb-6 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1">
          <span className="font-semibold">Thema</span>
          <select name="topic" defaultValue={topic} className="input">
            {TOPICS.map(([k, l]) => (
              <option key={k} value={k}>{l}</option>
            ))}
          </select>
        </label>
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

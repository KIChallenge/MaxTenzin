import { Building2, Compass, Eye, FilePen, FileText, ListChecks, Pill, Scale, Syringe } from "lucide-react";
import Link from "next/link";
import { BundleCard } from "@/components/BundleCard";
import { CareTeamCard } from "@/components/CareTeamCard";
import type { components } from "@/lib/api-types";
import type { DocumentSummary } from "@/lib/types";
import { UploadForm } from "./dokumente/UploadForm";
import type { CareTeam } from "@/lib/care";
import { OpenChatButton } from "@/components/OpenChatButton";
import type { SituationOverview } from "@/lib/situation";
import { api } from "@/lib/api";
import { cockpitRoute, fmtDate, fullName } from "@/lib/labels";
import type { ApiResult } from "@/lib/types";
import { getMe } from "@/lib/me";
import type { Notification } from "@/lib/types";

const TILES = [
  { href: "/dokumente", icon: FileText, title: "Dokumente", text: "Entlassungsbrief hochladen – wir zeigen, was drinsteht." },
  { href: "/leistungen", icon: Compass, title: "Leistungen", text: "Welche Leistungen kommen in Frage – mit Quellen." },
  { href: "/leistungen#antraege", icon: FilePen, title: "Anträge", text: "Formulare vorausgefüllt vorbereiten, als PDF-Entwurf." },
  { href: "/fall", icon: ListChecks, title: "Mein Fall", text: "Alle Schritte nach dem Spitalsaufenthalt im Blick." },
  { href: "/vorsorge", icon: Syringe, title: "Vorsorge", text: "Impfungen und Vorsorgeuntersuchungen laut Impfplan." },
  { href: "/stellen", icon: Building2, title: "Zuständige Stellen", text: "Wo Sie welchen Antrag einreichen." },
  { href: "/medikamente", icon: Pill, title: "Medikamente", text: "Kosten und Bewilligung laut Erstattungskodex." },
  { href: "/recht", icon: Scale, title: "Rechtsgrundlagen", text: "Gesetzestexte mit gültiger Fassung." },
  { href: "/transparenz", icon: Eye, title: "Transparenz", text: "Wer hat wann was abgefragt – Mensch oder KI." },
];

export default async function Cockpit() {
  const [me, inbox, situation, team] = await Promise.all([
    getMe(),
    api<Notification[]>("/api/notifications"),
    api<SituationOverview>("/api/situation"),
    api<CareTeam>("/api/identity/care-team"),
  ]);
  // Bundle for the current situation: newest copy of each document + the Lebenslage summary as text.
  const docs = await api<DocumentSummary[]>("/api/documents");
  const seen = new Set<string>();
  const docIds = (docs.ok ? [...docs.data].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at)) : [])
    .filter((d) => (seen.has(d.filename) ? false : (seen.add(d.filename), true)))
    .slice(0, 3)
    .map((d) => d.document_id);
  const latestLetter = (docs.ok ? [...docs.data].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at)) : []).find((d) => d.doc_type === "discharge_letter")?.document_id;
  const catalog = await api<components["schemas"]["Benefit"][]>("/api/benefits");
  const formOwner: Record<string, string> = {};
  for (const b of catalog.ok ? catalog.data : []) for (const f of b.form_ids ?? []) formOwner[f] ??= b.id;
  const bundle =
    docIds.length || (situation.ok && situation.data.summary_de)
      ? await api<components["schemas"]["Bundle"] | null>("/api/benefits/bundles/match", {
          method: "POST",
          body: { document_ids: docIds, text: situation.ok ? situation.data.summary_de || null : null, facts: {} },
        })
      : null;
  const subject = me.ok ? me.data.subject : null;
  const actor = me.ok ? me.data.actor : null;
  const forOther = subject && actor && subject.id !== actor.id;
  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_22rem]">
      <section>
        <h1 className="text-[1.75rem] leading-tight font-semibold tracking-[-0.02em]">
          Guten Tag, {actor?.first_name}
          {forOther && <span className="text-muted">. Sie handeln für {fullName(subject)}.</span>}
        </h1>
        <LebenslageSummary situation={situation} firstName={subject?.first_name ?? ""} subjectName={subject ? fullName(subject) : ""} />
        {bundle?.ok && bundle.data && (
          <div className="mt-5">
            <BundleCard bundle={bundle.data} formOwner={formOwner} documentId={latestLetter} canPrepare={!!me.ok && me.data.scopes.includes("prepare_applications")} />
          </div>
        )}
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="card flex flex-col justify-between gap-3 border-accent/30 bg-accent-soft">
            <div>
              <p className="font-semibold">Was möchten Sie heute erledigen?</p>
              <p className="text-muted">Lotsi fragt die Dienste für Sie ab – mit denselben Berechtigungen wie Sie.</p>
            </div>
            <div>
              <OpenChatButton>Frag Lotsi</OpenChatButton>
            </div>
          </div>
          {/* quick drop: straight to the document review after upload */}
          <UploadForm subjectName={subject ? fullName(subject) : ""} compact />
        </div>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {TILES.map((t) => (
            <li key={t.href}>
              <Link href={t.href} className="card flex h-full flex-col gap-1 transition hover:border-accent hover:shadow-md">
                <t.icon className="h-6 w-6 text-accent" aria-hidden />
                <span className="text-lg font-semibold text-accent-strong">{t.title}</span>
                <span className="text-muted">{t.text}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <aside aria-labelledby="inbox-h">
        <CareTeamCard team={team} firstName={subject?.first_name ?? ""} forOther={!!forOther} />
        <h2 id="inbox-h" className="text-lg font-semibold">
          Posteingang
        </h2>
        <div className="mt-3 space-y-3">
          {!inbox.ok && <p className="text-muted">Nachrichten derzeit nicht verfügbar.</p>}
          {inbox.ok && inbox.data.length === 0 && <p className="card text-muted">Keine neuen Nachrichten.</p>}
          {inbox.ok &&
            inbox.data.map((n) => (
              <article key={n.id} className={`card ${n.read ? "" : "border-l-4 border-l-accent"}`}>
                <p className="text-sm text-muted">{fmtDate(n.created_at)}</p>
                <h3 className="font-semibold">{n.title_de}</h3>
                <p className="text-muted">{n.body_de}</p>
                {n.link && (
                  <Link href={cockpitRoute(n.link)} className="link mt-1 inline-block">
                    Öffnen
                  </Link>
                )}
              </article>
            ))}
        </div>
      </aside>
    </div>
  );
}


/** Home: one compact Lebenslage card (summary, next deadlines, pending suggestions); the full view is /lebenslage. */
function LebenslageSummary({ situation, firstName, subjectName }: { situation: ApiResult<SituationOverview>; firstName: string; subjectName: string }) {
  if (!situation.ok) {
    return (
      <p className="card mt-5 text-muted">
        {situation.status === 403 ? `Für die Lebenslage hat ${subjectName} keine Berechtigung erteilt.` : "Lebenslage derzeit nicht verfügbar."}
      </p>
    );
  }
  const d = situation.data;
  const deadlines = d.effects.filter((e) => e.due_date).slice(0, 2);
  const pending = d.suggestions.length;
  return (
    <div className="card mt-5 flex flex-col gap-2">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-lg font-semibold">Lebenslage von {firstName}</h2>
        <span className="text-muted">{d.summary_de || "Keine aktuelle Lebenslage eingetragen"}</span>
        <Link href="/lebenslage" className="link ml-auto text-sm">
          Ansehen und ändern
        </Link>
      </div>
      {pending > 0 && (
        <p className="text-sm font-semibold text-warn">
          {pending} {pending === 1 ? "Vorschlag wartet" : "Vorschläge warten"} auf Ihre Zustimmung
        </p>
      )}
      {deadlines.length > 0 && (
        <ul className="space-y-1 text-sm">
          {deadlines.map((e) => (
            <li key={`${e.kind}-${e.title_de}`}>
              <span className="font-semibold">{e.title_de}</span>
              {e.due_date && <span className="ml-2 rounded bg-warn-soft px-1.5 py-0.5 text-warn">bis {fmtDate(e.due_date)}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

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


const INBOX_ORDER = ["situation", "case", "prevention"];

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
    <div className="grid gap-8 lg:grid-cols-[1fr_22rem] lg:in-[.chat-open]:grid-cols-1">
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
        <div className="mt-5 grid gap-4 md:grid-cols-2 md:in-[.chat-open]:grid-cols-1">
          {/* the chat is already open: no second invitation to it */}
          <div className="card flex flex-col justify-between gap-3 border-accent/30 bg-accent-soft in-[.chat-open]:hidden">
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
      </section>
      <aside aria-labelledby="inbox-h" className="lg:in-[.chat-open]:grid lg:in-[.chat-open]:grid-cols-2 lg:in-[.chat-open]:items-start lg:in-[.chat-open]:gap-6">
        <CareTeamCard team={team} firstName={subject?.first_name ?? ""} forOther={!!forOther} />
        <section aria-labelledby="inbox-h" className="card">
          <div className="mb-2 flex items-baseline justify-between gap-2">
            <h2 id="inbox-h" className="text-lg font-semibold">
              Posteingang{inbox.ok && inbox.data.length ? ` (${inbox.data.length})` : ""}
            </h2>
            <Link href="/posteingang" className="link text-sm">
              Alle Nachrichten
            </Link>
          </div>
          {!inbox.ok && <p className="text-muted">Nachrichten derzeit nicht verfügbar.</p>}
          {inbox.ok && inbox.data.length === 0 && <p className="text-muted">Keine neuen Nachrichten.</p>}
          {inbox.ok && inbox.data.length > 0 && (
            <ul className="divide-y divide-line">
              {/* deadlines first (Lebenslage), then the case, then prevention */}
              {[...inbox.data]
                .sort((x, y) => INBOX_ORDER.indexOf(x.kind) - INBOX_ORDER.indexOf(y.kind))
                .slice(0, 3)
                .map((n) => (
                  <li key={n.id} className="py-2">
                    <Link href={n.link ? cockpitRoute(n.link) : "/posteingang"} className="font-semibold hover:underline">
                      {n.title_de}
                    </Link>
                    <p className="text-sm text-muted">{fmtDate(n.created_at)}</p>
                  </li>
                ))}
            </ul>
          )}
        </section>
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

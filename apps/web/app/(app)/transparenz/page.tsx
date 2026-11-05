import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { fmtDateTime, fullName, SCOPE_LABELS } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { AuditEvent, Person, Scope } from "@/lib/types";

type Row = AuditEvent & { count: number };

/** Collapse runs of identical events (e.g. the wizard's 2-second polling) into one row. */
function collapse(events: AuditEvent[]): Row[] {
  const out: Row[] = [];
  for (const e of events) {
    const last = out[out.length - 1];
    if (last && last.actor_id === e.actor_id && last.via === e.via && last.tool === e.tool && last.method === e.method && last.path === e.path && last.status === e.status) last.count++;
    else out.push({ ...e, count: 1 });
  }
  return out;
}

export default async function AuditPage({ searchParams }: { searchParams: Promise<{ all?: string; only?: string; limit?: string; session?: string }> }) {
  const sp = await searchParams;
  const limit = Math.min(Number(sp.limit) || 60, 500);
  const [me, events, personas] = await Promise.all([
    getMe(),
    api<AuditEvent[]>(`/api/audit?limit=${limit}`),
    api<Person[]>("/api/identity/personas"),
  ]);
  const name = me.ok ? fullName(me.data.subject) : "";
  const names = new Map((personas.ok ? personas.data : []).map((p) => [p.id, fullName(p)]));
  const who = (id?: string | null) => (id ? names.get(id) ?? id : "–");

  // Session checks (who am I / whom may I represent) run on every page load and bury the data accesses.
  const isSessionCheck = (e: AuditEvent) => e.method === "GET" && /^\/api\/identity\/(me|represented)$/.test(e.path) && e.status < 400;
  const sessionChecks = events.ok ? events.data.filter(isSessionCheck).length : 0;
  const visibleEvents = events.ok ? (sp.session ? events.data : events.data.filter((e) => !isSessionCheck(e))) : [];
  let rows: Row[] = sp.all ? visibleEvents.map((e) => ({ ...e, count: 1 })) : collapse(visibleEvents);
  if (sp.only === "agent") rows = rows.filter((r) => r.via === "agent");
  if (sp.only === "denied") rows = rows.filter((r) => !r.allowed || r.status === 403);
  const denied = events.ok ? events.data.filter((e) => !e.allowed || e.status === 403).length : 0;
  const viaAgent = events.ok ? events.data.filter((e) => e.via === "agent").length : 0;

  const filters: [string, string][] = [
    ["", "Alle"],
    ["agent", `Nur KI (${viaAgent})`],
    ["denied", `Abgelehnt (${denied})`],
  ];

  return (
    <>
      <PageTitle eyebrow="Transparenz" title={`Wer hat auf Daten von ${name} zugegriffen?`}>
        Jeder Zugriff – ob durch Sie oder durch den KI-Lotsen – wird protokolliert. Der Lotse hat keine Sonderrechte.
      </PageTitle>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {filters.map(([k, label]) => (
          <a key={k} href={`/transparenz${k ? `?only=${k}` : ""}`} className={(sp.only ?? "") === k ? "btn-primary py-1" : "btn-secondary py-1"}>
            {label}
          </a>
        ))}
        <span className="ml-auto flex flex-wrap gap-x-4">
          <a href={sp.session ? "/transparenz" : "/transparenz?session=1"} className="link">
            {sp.session ? "Anmeldeprüfungen ausblenden" : `Anmeldeprüfungen einblenden (${sessionChecks})`}
          </a>
          <a href={sp.all ? "/transparenz" : "/transparenz?all=1"} className="link">
            {sp.all ? "Wiederholte Abrufe zusammenfassen" : "Jeden Abruf einzeln zeigen"}
          </a>
        </span>
      </div>
      {!events.ok ? (
        <ApiError status={events.status} detail={events.detail} subjectName={name} />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Zugriffsprotokoll</caption>
            <thead className="bg-paper text-sm">
              <tr>
                {["Zeit", "Wer · für wen", "Über", "Aktion", "Berechtigung", "Ergebnis", "Quellen / Regeln"].map((h) => (
                  <th key={h} scope="col" className="px-3 py-1.5 font-bold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((e) => {
                const isDenied = !e.allowed || e.status === 403;
                return (
                  <tr key={e.id} className={isDenied ? "bg-danger-soft" : e.via === "agent" ? "bg-accent-soft/50" : ""}>
                    <td className="px-3 py-1.5 text-sm whitespace-nowrap">{fmtDateTime(e.ts)}</td>
                    <td className="px-3 py-1.5 whitespace-nowrap">
                      <strong>{who(e.actor_id)}</strong>
                      {e.subject_id && e.subject_id !== e.actor_id && <span className="block text-sm text-muted">für {who(e.subject_id)}</span>}
                    </td>
                    <td className="px-3 py-1.5 whitespace-nowrap">
                      {e.via === "agent" ? <span className="font-bold text-accent-strong">🤖 KI-Lotse</span> : "👤 Oberfläche"}
                      {e.tool && <span className="block text-sm text-muted">{e.tool}</span>}
                    </td>
                    <td className="px-3 py-1.5 text-sm">
                      <code className="whitespace-nowrap" title={`${e.method} ${e.path}`}>
                        {e.method} {shortPath(e.path)}
                      </code>
                      {e.count > 1 && <span className="ml-1 rounded bg-neutral-soft px-1 font-bold">×{e.count}</span>}
                    </td>
                    <td className="px-3 py-1.5 text-sm">{e.scope_required ? SCOPE_LABELS[e.scope_required as Scope] ?? e.scope_required : "–"}</td>
                    <td className="px-3 py-1.5 text-sm font-bold">
                      {isDenied ? <span className="text-danger">⛔ abgelehnt ({e.status})</span> : e.status < 400 ? <span className="text-ok">✓ {e.status}</span> : <span className="text-warn">{e.status}</span>}
                    </td>
                    <td className="px-3 py-1.5 text-sm">{[...(e.sources ?? []), ...(e.rule_ids ?? [])].join(", ") || "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length === 0 && <p className="p-4 text-muted">Keine Einträge.</p>}
          {events.data.length >= limit && (
            <p className="border-t border-line p-3">
              <a className="link" href={`/transparenz?limit=${limit + 100}${sp.only ? `&only=${sp.only}` : ""}${sp.all ? "&all=1" : ""}`}>
                Ältere Einträge laden
              </a>
            </p>
          )}
        </div>
      )}
    </>
  );
}

/** Long ids (UUIDs, doc-xxxx) are noise in an audit table – keep the first characters, full path stays in the tooltip. */
function shortPath(path: string) {
  return path.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, (m) => `${m.slice(0, 8)}…`);
}

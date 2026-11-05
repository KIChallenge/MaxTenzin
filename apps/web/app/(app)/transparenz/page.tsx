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

export default async function AuditPage({ searchParams }: { searchParams: Promise<{ all?: string; only?: string }> }) {
  const sp = await searchParams;
  const [me, events, personas] = await Promise.all([
    getMe(),
    api<AuditEvent[]>("/api/audit?limit=300"),
    api<Person[]>("/api/identity/personas"),
  ]);
  const name = me.ok ? fullName(me.data.subject) : "";
  const names = new Map((personas.ok ? personas.data : []).map((p) => [p.id, fullName(p)]));
  const who = (id?: string | null) => (id ? names.get(id) ?? id : "–");

  let rows: Row[] = events.ok ? (sp.all ? events.data.map((e) => ({ ...e, count: 1 })) : collapse(events.data)) : [];
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
        <a href={sp.all ? "/transparenz" : "/transparenz?all=1"} className="link ml-auto">
          {sp.all ? "Wiederholte Abrufe zusammenfassen" : "Jeden Abruf einzeln zeigen"}
        </a>
      </div>
      {!events.ok ? (
        <ApiError status={events.status} detail={events.detail} subjectName={name} />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full text-left">
            <caption className="sr-only">Zugriffsprotokoll</caption>
            <thead className="bg-paper text-sm">
              <tr>
                {["Zeit", "Wer", "Für wen", "Über", "Werkzeug", "Aktion", "Berechtigung", "Ergebnis", "Quellen / Regeln"].map((h) => (
                  <th key={h} scope="col" className="px-3 py-2 font-bold">
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
                    <td className="px-3 py-2 text-sm whitespace-nowrap">{fmtDateTime(e.ts)}</td>
                    <td className="px-3 py-2">{who(e.actor_id)}</td>
                    <td className="px-3 py-2">{who(e.subject_id)}</td>
                    <td className="px-3 py-2">
                      {e.via === "agent" ? <span className="font-bold text-accent-strong">🤖 KI-Lotse</span> : "👤 Oberfläche"}
                    </td>
                    <td className="px-3 py-2 text-sm">{e.tool ?? "–"}</td>
                    <td className="px-3 py-2 text-sm">
                      <code>
                        {e.method} {e.path}
                      </code>
                      {e.count > 1 && <span className="ml-1 rounded bg-neutral-soft px-1 font-bold">×{e.count}</span>}
                    </td>
                    <td className="px-3 py-2 text-sm">{e.scope_required ? SCOPE_LABELS[e.scope_required as Scope] ?? e.scope_required : "–"}</td>
                    <td className="px-3 py-2 text-sm font-bold">
                      {isDenied ? <span className="text-danger">⛔ abgelehnt ({e.status})</span> : e.status < 400 ? <span className="text-ok">✓ {e.status}</span> : <span className="text-warn">{e.status}</span>}
                    </td>
                    <td className="px-3 py-2 text-sm">{[...(e.sources ?? []), ...(e.rule_ids ?? [])].join(", ") || "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.length === 0 && <p className="p-4 text-muted">Keine Einträge.</p>}
        </div>
      )}
    </>
  );
}

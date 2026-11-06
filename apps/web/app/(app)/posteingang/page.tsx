import Link from "next/link";
import { PageTitle } from "@/components/PageTitle";
import { api } from "@/lib/api";
import { cockpitRoute, fmtDate } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { Notification } from "@/lib/types";

// Deadlines first, then the case, then prevention.
const GROUPS: [string, string][] = [
  ["situation", "Fristen aus der Lebenslage"],
  ["case", "Mein Fall"],
  ["prevention", "Vorsorge & Impfungen"],
];

export default async function InboxPage() {
  const [me, inbox] = await Promise.all([getMe(), api<Notification[]>("/api/notifications")]);
  const name = me.ok ? me.data.subject.first_name : "";
  const all = inbox.ok ? inbox.data : [];
  const known = new Set(GROUPS.map(([k]) => k));
  const groups = [...GROUPS, ["other", "Weitere"] as [string, string]]
    .map(([k, label]) => ({ label, items: all.filter((n) => (known.has(n.kind) ? n.kind === k : k === "other")) }))
    .filter((g) => g.items.length);
  return (
    <div className="max-w-3xl">
      <PageTitle eyebrow="Posteingang" title={`Nachrichten für ${name}`}>
        Erinnerungen und Hinweise aus festen Regeln – jede mit Quelle. Nichts davon wird automatisch eingereicht.
      </PageTitle>
      {!inbox.ok && <p className="text-muted">Nachrichten derzeit nicht verfügbar.</p>}
      {inbox.ok && all.length === 0 && <p className="card text-muted">Keine neuen Nachrichten.</p>}
      <div className="space-y-8">
        {groups.map((g) => (
          <section key={g.label} aria-label={g.label}>
            <h2 className="mb-2 font-semibold text-muted">
              {g.label} ({g.items.length})
            </h2>
            <ul className="divide-y divide-line rounded-xl border border-line bg-surface">
              {g.items.map((n) => (
                <li key={n.id} className={`flex flex-wrap items-start gap-x-4 gap-y-1 px-5 py-3 ${n.read ? "" : "border-l-4 border-l-accent"}`}>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">{n.title_de}</p>
                    <p className="text-sm text-muted">{n.body_de}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1 text-sm">
                    <span className="text-muted">{fmtDate(n.created_at)}</span>
                    {n.link && (
                      <Link href={cockpitRoute(n.link)} className="link">
                        Öffnen
                      </Link>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

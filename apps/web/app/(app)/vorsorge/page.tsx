import Link from "next/link";
import { CalendarPlus, MessageCircleQuestion, Syringe } from "lucide-react";
import { ApiError } from "@/components/ApiError";
import { Badge } from "@/components/Badge";
import { PageTitle } from "@/components/PageTitle";
import { SourceList } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { fmtDate, fullName, PREVENTION_STATUS } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { PreventionItem, PreventionOverview } from "@/lib/types";

// Prevention item id → appointment topic (provider topics of the appointments service).
const TOPIC: Record<string, string> = { vu: "vorsorgeuntersuchung", darmkrebs: "darmkrebs_vorsorge" };
const topicFor = (id: string) => TOPIC[id] ?? id;

export default async function PreventionPage() {
  const [me, r] = await Promise.all([getMe(), api<PreventionOverview>("/api/prevention/overview")]);
  const name = me.ok ? fullName(me.data.subject) : "";
  if (!r.ok) {
    return (
      <>
        <PageTitle title={`Vorsorge & Impfungen – ${name}`} />
        <ApiError status={r.status} detail={r.detail} subjectName={name} />
      </>
    );
  }
  const o = r.data;
  const due = o.items.filter((i) => i.status === "due" || i.status === "upcoming");
  const unclear = o.items.filter((i) => i.status === "not_documented");
  const ok = o.items.filter((i) => i.status === "up_to_date");

  return (
    <>
      <PageTitle title={`Vorsorge & Impfungen – ${name}`}>Hinweise laut Österreichischem Impfplan und den Angeboten der Krankenversicherung.</PageTitle>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-6">
          {/* 1 · Was jetzt zu tun ist */}
          <section aria-labelledby="due-h" className="rounded-xl border border-accent/25 bg-accent-soft/50 p-4">
            <h2 id="due-h" className="font-semibold">
              Was jetzt zu tun ist
            </h2>
            {due.length === 0 ? (
              <p className="mt-1 text-sm text-muted">Derzeit ist laut Impfplan nichts fällig.</p>
            ) : (
              <ul className="mt-2 divide-y divide-accent/15">
                {due.map((it) => (
                  <Item key={it.id} it={it} action="book" />
                ))}
              </ul>
            )}
          </section>

          {/* 2 · Mit der Ärztin klären */}
          {unclear.length > 0 && (
            <section aria-labelledby="unclear-h">
              <h2 id="unclear-h" className="font-semibold">
                Mit Ärztin bzw. Arzt klären
              </h2>
              <p className="mb-2 text-sm text-muted">Nicht im e-Impfpass dokumentiert – das heißt nicht, dass etwas fehlt. Bitte beim nächsten Termin ansprechen.</p>
              <ul className="divide-y divide-line rounded-xl border border-line bg-surface px-4">
                {unclear.map((it) => (
                  <Item key={it.id} it={it} action="ask" />
                ))}
              </ul>
            </section>
          )}

          {ok.length > 0 && (
            <section aria-labelledby="ok-h">
              <h2 id="ok-h" className="mb-2 font-semibold">
                Dokumentiert und aktuell
              </h2>
              <ul className="divide-y divide-line rounded-xl border border-line bg-surface px-4">
                {ok.map((it) => (
                  <Item key={it.id} it={it} />
                ))}
              </ul>
            </section>
          )}

          <footer className="border-t border-line pt-3 text-sm text-muted">
            {o.disclaimer_de} Stand: {fmtDate(o.as_of)}.
          </footer>
        </div>

        <aside className="card h-fit">
          <h2 className="flex items-center gap-2 font-semibold">
            <Syringe className="h-4 w-4 text-accent" aria-hidden /> Im e-Impfpass dokumentiert
          </h2>
          {o.vaccinations.length === 0 ? (
            <p className="mt-1 text-sm text-muted">
              Keine Einträge. <Link href="/dokumente" className="link">e-Impfpass hochladen</Link>
            </p>
          ) : (
            <ul className="mt-1.5 divide-y divide-line text-sm">
              {o.vaccinations.map((v, i) => (
                <li key={i} className="py-1.5">
                  <p className="font-semibold">{v.disease}</p>
                  <p className="text-muted">
                    {fmtDate(v.date)} · {v.vaccine}
                    {v.dose_label && ` · ${v.dose_label}`}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </>
  );
}

function Item({ it, action }: { it: PreventionItem; action?: "book" | "ask" }) {
  const st = PREVENTION_STATUS[it.status];
  const label = it.kind !== "vaccination" && it.status === "due" ? "empfohlen – kostenloses Angebot" : st.label;
  const meta = [
    it.last_date && `zuletzt ${fmtDate(it.last_date)}`,
    it.due_date && `empfohlen bis ${fmtDate(it.due_date)}`,
    it.cost_de && it.cost_de,
  ].filter(Boolean);
  return (
    <li className="flex flex-wrap items-start gap-x-3 gap-y-1.5 py-2.5">
      <div className="min-w-0 flex-1">
        <p className="font-semibold">
          {it.title_de} {action !== "ask" && <Badge tone={st.tone}>{label}</Badge>}
        </p>
        <p className="text-sm text-muted">{it.explanation_de}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 text-sm text-muted">
          {meta.length > 0 && <span>{meta.join(" · ")}</span>}
          <SourceList sources={it.sources} />
        </div>
      </div>
      {action === "book" && (
        <Link href={`/termine?topic=${encodeURIComponent(topicFor(it.id))}&suche=1`} className="btn-primary py-1 text-sm">
          <CalendarPlus className="h-4 w-4" aria-hidden /> Termin suchen
        </Link>
      )}
      {action === "ask" && (
        <Link href="/termine?wo=provider&suche=1" className="btn-ghost px-2 py-1 text-sm">
          <MessageCircleQuestion className="h-4 w-4" aria-hidden /> Bei Hausärztin ansprechen
        </Link>
      )}
    </li>
  );
}

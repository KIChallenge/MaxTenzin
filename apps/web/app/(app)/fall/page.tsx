import { Check } from "lucide-react";
import Link from "next/link";
import { createCase } from "@/app/actions";
import { ApiError } from "@/components/ApiError";
import { PageTitle } from "@/components/PageTitle";
import { SourceChip } from "@/components/SourceChip";
import { api } from "@/lib/api";
import { fmtDate, fullName } from "@/lib/labels";
import { getMe } from "@/lib/me";
import type { Case } from "@/lib/types";
import { StepStatusSelect } from "./StepStatusSelect";

export default async function CasePage({ searchParams }: { searchParams: Promise<{ error?: string; status?: string }> }) {
  const sp = await searchParams;
  const [me, cases] = await Promise.all([getMe(), api<Case[]>("/api/cases")]);
  const name = me.ok ? fullName(me.data.subject) : "";
  return (
    <>
      <PageTitle eyebrow="Mein Fall" title={`Schritte für ${name}`}>
        Alles, was nach dem Spitalsaufenthalt zu tun ist – und wer dafür zuständig ist.
      </PageTitle>
      {sp.error && (
        <div className="mb-6">
          <ApiError status={Number(sp.status ?? 0)} detail={sp.error} subjectName={name} />
        </div>
      )}
      {!cases.ok ? (
        <ApiError status={cases.status} detail={cases.detail} subjectName={name} />
      ) : cases.data.length === 0 ? (
        <div className="card flex flex-wrap items-center gap-4">
          <p className="flex-1 text-lg">
            Noch kein Fall angelegt. Wir übernehmen die offenen Aufgaben aus dem zuletzt hochgeladenen Dokument.
          </p>
          <form action={createCase}>
            <button className="btn-primary">Fall aus Dokument anlegen</button>
          </form>
          <Link href="/dokumente" className="link">Dokument hochladen</Link>
        </div>
      ) : (
        cases.data.map((c) => {
          const done = c.steps.filter((s) => s.status === "done").length;
          // Same source on every step (e.g. "Entlassungsbefund.pdf – offene Aufgaben") → show it once in the header.
          const sharedSource = c.steps.every((s) => s.source && s.source.label === c.steps[0].source?.label) ? c.steps[0].source : null;
          return (
            <section key={c.id} className="mb-8">
              <div className="mb-3 flex flex-wrap items-end gap-3">
                <h2 className="text-xl font-semibold">{c.title_de}</h2>
                <span className="text-muted">
                  angelegt {fmtDate(c.created_at)} · {done} von {c.steps.length} erledigt
                  {sharedSource && (
                    <>
                      {" · Quelle: "}
                      <SourceChip source={sharedSource} />
                    </>
                  )}
                </span>
              </div>
              <ol className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
                {c.steps.map((s, i) => {
                  return (
                    <li key={s.id} className={`flex flex-wrap items-center gap-3 px-4 py-2.5 ${s.status === "done" ? "opacity-70" : ""}`}>
                      <span aria-hidden className={`grid h-7 w-7 shrink-0 text-sm place-items-center rounded-full font-semibold ${s.status === "done" ? "bg-ok text-white" : "bg-accent-soft text-accent-strong"}`}>
                        {s.status === "done" ? <Check className="h-5 w-5" aria-hidden /> : i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className={`font-semibold ${s.status === "done" ? "line-through" : ""}`}>{s.title_de}</p>
                        <p className="text-sm text-muted">
                          Zuständig: {s.responsible_de}
                          {s.due_date ? ` · bis ${fmtDate(s.due_date)}` : ""}
                        </p>
                        <div className="mt-0.5 flex flex-wrap items-center gap-3 text-sm">
                          {s.source && s.source.label !== sharedSource?.label && <SourceChip source={s.source} />}
                          {s.benefit_id && <Link href={`/leistungen#${s.benefit_id}`} className="link">Leistung ansehen</Link>}
                          {s.form_session_id && <Link href={`/forms/${s.form_session_id}`} className="link">Antrag öffnen</Link>}
                        </div>
                      </div>
                      <StepStatusSelect caseId={c.id} stepId={s.id} status={s.status ?? "open"} label={s.title_de} />
                    </li>
                  );
                })}
              </ol>
            </section>
          );
        })
      )}
    </>
  );
}
